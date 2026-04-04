from datetime import datetime

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str
    snippet: str
    section: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str
    route: str = "hybrid"
    confidence: float | None = None
    trace_id: str | None = None
    critic_passed: bool | None = None
    followups: list[str] = []
    conversation_id: str | None = None


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=4, max_length=128)
    vote: str = Field(pattern="^(up|down)$")
    comment: str | None = Field(default=None, max_length=500)


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
