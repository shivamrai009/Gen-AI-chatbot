from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.embedder import Embedder
from app.services.gemini_client import GeminiClient
from app.services.retriever import VectorRetriever
from app.services.vector_store import create_vector_store

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
embedder = Embedder()
vector_store = create_vector_store(settings=settings)
retriever = VectorRetriever(embedder=embedder, vector_store=vector_store)
gemini_client = GeminiClient()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        sources = await retriever.search(request.question, top_k=settings.max_context_chunks)
        answer = await gemini_client.generate_answer(request.question, sources)
        return ChatResponse(answer=answer, sources=sources, model=settings.gemini_model)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat request failed: {exc}") from exc
