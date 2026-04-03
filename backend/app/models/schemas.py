from datetime import datetime

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str
    snippet: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
