"""Conversation history CRUD endpoints."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.auth import decode_token
from app.core.config import get_settings
from app.services.chat_store import ChatStore

router = APIRouter(prefix="/conversations", tags=["conversations"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_chat_store() -> ChatStore:
    return ChatStore(get_settings().chat_db_path)


def current_username(token: str = Depends(oauth2_scheme)) -> str:
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username


# ── Request / Response models ─────────────────────────────────

class CreateConversationRequest(BaseModel):
    title: str = "New conversation"


class AddMessageRequest(BaseModel):
    role: str
    content: str
    sources: list = []
    route: str | None = None
    trace_id: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list
    route: str | None
    trace_id: str | None
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────

@router.get("", response_model=list[ConversationOut])
def list_conversations(
    username: str = Depends(current_username),
    store: ChatStore = Depends(get_chat_store),
):
    rows = store.list_conversations(username)
    return [ConversationOut(id=r.id, title=r.title, created_at=r.created_at, updated_at=r.updated_at) for r in rows]


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(
    req: CreateConversationRequest,
    username: str = Depends(current_username),
    store: ChatStore = Depends(get_chat_store),
):
    conv_id = str(uuid4())
    row = store.create_conversation(conv_id, username, req.title)
    return ConversationOut(id=row.id, title=row.title, created_at=row.created_at, updated_at=row.updated_at)


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
def get_messages(
    conv_id: str,
    username: str = Depends(current_username),
    store: ChatStore = Depends(get_chat_store),
):
    if not store.get_conversation(conv_id, username):
        raise HTTPException(status_code=404, detail="Conversation not found")
    rows = store.list_messages(conv_id)
    return [
        MessageOut(id=r.id, role=r.role, content=r.content,
                   sources=r.sources, route=r.route, trace_id=r.trace_id,
                   created_at=r.created_at)
        for r in rows
    ]


@router.post("/{conv_id}/messages", response_model=MessageOut, status_code=201)
def add_message(
    conv_id: str,
    req: AddMessageRequest,
    username: str = Depends(current_username),
    store: ChatStore = Depends(get_chat_store),
):
    if not store.get_conversation(conv_id, username):
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg_id = str(uuid4())
    row = store.add_message(
        msg_id, conv_id, req.role, req.content,
        req.sources, req.route, req.trace_id,
    )
    return MessageOut(id=row.id, role=row.role, content=row.content,
                      sources=row.sources, route=row.route, trace_id=row.trace_id,
                      created_at=row.created_at)


@router.patch("/{conv_id}/title")
def rename_conversation(
    conv_id: str,
    body: dict,
    username: str = Depends(current_username),
    store: ChatStore = Depends(get_chat_store),
):
    if not store.get_conversation(conv_id, username):
        raise HTTPException(status_code=404, detail="Conversation not found")
    store.update_title(conv_id, body.get("title", "Untitled"))
    return {"status": "ok"}


@router.delete("/{conv_id}", status_code=204)
def delete_conversation(
    conv_id: str,
    username: str = Depends(current_username),
    store: ChatStore = Depends(get_chat_store),
):
    if not store.delete_conversation(conv_id, username):
        raise HTTPException(status_code=404, detail="Conversation not found")
