"""SQLite-backed persistent chat history."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ConversationRow:
    id: str
    username: str
    title: str
    created_at: str
    updated_at: str


@dataclass
class MessageRow:
    id: str
    conversation_id: str
    role: str          # "user" | "assistant"
    content: str
    sources: list      # JSON-serialised list
    route: str | None
    trace_id: str | None
    created_at: str


class ChatStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT NOT NULL DEFAULT '[]',
                    route TEXT,
                    trace_id TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_msg_conv
                    ON messages(conversation_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_conv_user
                    ON conversations(username, updated_at DESC);
            """)

    # ── Conversations ────────────────────────────────────────

    def create_conversation(self, conv_id: str, username: str, title: str) -> ConversationRow:
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (id, username, title, created_at, updated_at) VALUES (?,?,?,?,?)",
                (conv_id, username, title, now, now),
            )
        return ConversationRow(id=conv_id, username=username, title=title, created_at=now, updated_at=now)

    def list_conversations(self, username: str, limit: int = 30) -> list[ConversationRow]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE username=? ORDER BY updated_at DESC LIMIT ?",
                (username, limit),
            ).fetchall()
        return [ConversationRow(**dict(r)) for r in rows]

    def get_conversation(self, conv_id: str, username: str) -> ConversationRow | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id=? AND username=?",
                (conv_id, username),
            ).fetchone()
        return ConversationRow(**dict(row)) if row else None

    def update_title(self, conv_id: str, title: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET title=?, updated_at=? WHERE id=?",
                (title, _now(), conv_id),
            )

    def touch_conversation(self, conv_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (_now(), conv_id),
            )

    def delete_conversation(self, conv_id: str, username: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
            cur = conn.execute(
                "DELETE FROM conversations WHERE id=? AND username=?", (conv_id, username)
            )
        return cur.rowcount > 0

    # ── Messages ─────────────────────────────────────────────

    def add_message(
        self,
        msg_id: str,
        conv_id: str,
        role: str,
        content: str,
        sources: list | None = None,
        route: str | None = None,
        trace_id: str | None = None,
    ) -> MessageRow:
        now = _now()
        sources_json = json.dumps(sources or [])
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, sources, route, trace_id, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (msg_id, conv_id, role, content, sources_json, route, trace_id, now),
            )
        self.touch_conversation(conv_id)
        return MessageRow(
            id=msg_id, conversation_id=conv_id, role=role,
            content=content, sources=sources or [],
            route=route, trace_id=trace_id, created_at=now,
        )

    def list_messages(self, conv_id: str) -> list[MessageRow]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at",
                (conv_id,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d["sources"])
            result.append(MessageRow(**d))
        return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
