import json
from dataclasses import asdict, dataclass
from pathlib import Path
# pyright: reportMissingImports=false

import numpy as np
import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings


@dataclass
class IndexedChunk:
    id: str
    title: str
    url: str
    snippet: str
    chunk_text: str
    embedding: list[float]


class LocalVectorStore:
    def __init__(self, index_path: str) -> None:
        self.index_path = Path(index_path)

    def save(self, chunks: list[IndexedChunk]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(chunk) for chunk in chunks]
        self.index_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def upsert_chunks(self, chunks: list[IndexedChunk]) -> None:
        if not chunks:
            return

        existing = self.load()
        chunk_map = {chunk.id: chunk for chunk in existing}
        for chunk in chunks:
            chunk_map[chunk.id] = chunk
        self.save(list(chunk_map.values()))

    def clear(self) -> None:
        self.save([])

    def delete_by_urls(self, urls: list[str]) -> None:
        if not urls:
            return
        url_set = set(urls)
        kept = [chunk for chunk in self.load() if chunk.url not in url_set]
        self.save(kept)

    def get_indexed_urls(self) -> set[str]:
        return {chunk.url for chunk in self.load()}

    def load(self) -> list[IndexedChunk]:
        if not self.index_path.exists():
            return []

        raw = self.index_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return [IndexedChunk(**item) for item in data]

    def query_similar(self, query_embedding: list[float], top_k: int) -> list[IndexedChunk]:
        chunks = self.load()
        if not chunks:
            return []

        vec_a = np.array(query_embedding, dtype=float)
        scored = sorted(
            ((self._cosine_similarity(vec_a, np.array(chunk.embedding, dtype=float)), chunk) for chunk in chunks),
            key=lambda item: item[0],
            reverse=True,
        )
        return [chunk for _, chunk in scored[:top_k]]

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        if vec_a.size == 0 or vec_b.size == 0:
            return -1.0

        size = min(vec_a.size, vec_b.size)
        left = vec_a[:size]
        right = vec_b[:size]
        denom = np.linalg.norm(left) * np.linalg.norm(right)
        if denom == 0:
            return -1.0
        return float(np.dot(left, right) / denom)


class PgVectorStore:
    def __init__(self, dsn: str, table_name: str, embedding_dimensions: int) -> None:
        if not dsn:
            raise ValueError("POSTGRES_DSN is required when VECTOR_BACKEND=postgres")
        self.dsn = dsn
        self.table_name = table_name
        self.embedding_dimensions = embedding_dimensions
        self._ensure_schema()

    def save(self, chunks: list[IndexedChunk]) -> None:
        self.upsert_chunks(chunks)

    def upsert_chunks(self, chunks: list[IndexedChunk]) -> None:
        if not chunks:
            return

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name} (id, title, url, snippet, chunk_text, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s::vector)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            title = EXCLUDED.title,
                            url = EXCLUDED.url,
                            snippet = EXCLUDED.snippet,
                            chunk_text = EXCLUDED.chunk_text,
                            embedding = EXCLUDED.embedding
                        """,
                        (
                            chunk.id,
                            chunk.title,
                            chunk.url,
                            chunk.snippet,
                            chunk.chunk_text,
                            self._vector_literal(chunk.embedding),
                        ),
                    )
            conn.commit()

    def clear(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self.table_name}")
            conn.commit()

    def delete_by_urls(self, urls: list[str]) -> None:
        if not urls:
            return
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self.table_name} WHERE url = ANY(%s)", (urls,))
            conn.commit()

    def get_indexed_urls(self) -> set[str]:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT DISTINCT url FROM {self.table_name}")
                rows = cur.fetchall()
        return {row["url"] for row in rows}

    def load(self) -> list[IndexedChunk]:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, title, url, snippet, chunk_text, embedding::text AS embedding_text FROM {self.table_name}"
                )
                rows = cur.fetchall()

        return [
            IndexedChunk(
                id=row["id"],
                title=row["title"],
                url=row["url"],
                snippet=row["snippet"],
                chunk_text=row["chunk_text"],
                embedding=self._parse_vector_text(row["embedding_text"]),
            )
            for row in rows
        ]

    def query_similar(self, query_embedding: list[float], top_k: int) -> list[IndexedChunk]:
        query_literal = self._vector_literal(query_embedding)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, title, url, snippet, chunk_text, embedding::text AS embedding_text
                    FROM {self.table_name}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_literal, top_k),
                )
                rows = cur.fetchall()

        return [
            IndexedChunk(
                id=row["id"],
                title=row["title"],
                url=row["url"],
                snippet=row["snippet"],
                chunk_text=row["chunk_text"],
                embedding=self._parse_vector_text(row["embedding_text"]),
            )
            for row in rows
        ]

    def _ensure_schema(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        snippet TEXT NOT NULL,
                        chunk_text TEXT NOT NULL,
                        embedding vector({self.embedding_dimensions}) NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx ON {self.table_name} USING hnsw (embedding vector_cosine_ops)"
                )
            conn.commit()

    def _vector_literal(self, values: list[float]) -> str:
        if len(values) < self.embedding_dimensions:
            padded = values + [0.0] * (self.embedding_dimensions - len(values))
            values = padded
        elif len(values) > self.embedding_dimensions:
            values = values[: self.embedding_dimensions]
        return "[" + ",".join(str(float(value)) for value in values) + "]"

    def _parse_vector_text(self, vector_text: str) -> list[float]:
        stripped = vector_text.strip().strip("[]")
        if not stripped:
            return []
        return [float(value) for value in stripped.split(",")]


def create_vector_store(settings: Settings, base_dir: str | None = None) -> LocalVectorStore | PgVectorStore:
    backend = settings.vector_backend.strip().lower()
    if backend == "postgres":
        return PgVectorStore(
            dsn=settings.postgres_dsn,
            table_name=settings.pgvector_table,
            embedding_dimensions=settings.embedding_dimensions,
        )

    index_path = settings.vector_index_path
    if base_dir:
        index_path = str(Path(base_dir) / settings.vector_index_path)
    return LocalVectorStore(index_path=index_path)
