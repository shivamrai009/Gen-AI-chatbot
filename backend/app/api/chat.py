import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.critic import CriticService
from app.services.embedder import Embedder
from app.services.entity_extractor import EntityExtractor
from app.services.guardrails import GuardrailService
from app.services.graph_retriever import GraphRetriever
from app.services.graph_store import GraphStore
from app.services.llm_provider import LLMProvider
from app.services.orchestrator import ChatOrchestrator
from app.services.retriever import VectorRetriever
from app.services.router import RouterService
from app.services.telemetry import TelemetryService
from app.services.vector_store import create_vector_store

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
embedder = Embedder()
vector_store = create_vector_store(settings=settings)
graph_store = GraphStore(settings.graph_path)
graph_retriever = GraphRetriever(extractor=EntityExtractor(), graph_store=graph_store)
retriever = VectorRetriever(embedder=embedder, vector_store=vector_store, graph_retriever=graph_retriever)
orchestrator = ChatOrchestrator(
    router=RouterService(),
    retriever=retriever,
    provider=LLMProvider(),
    critic=CriticService(),
    guardrails=GuardrailService(),
    telemetry=TelemetryService(settings.telemetry_path),
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await orchestrator.run(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat request failed: {exc}") from exc


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def event_stream():
        try:
            response = await orchestrator.run(request)
            for token in response.answer.split(" "):
                # Escape newlines so SSE doesn't split a single token across lines
                safe = token.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "")
                yield f"data: {safe} \n\n"
            yield f"event: meta\ndata: {response.model}|{response.route}|{response.trace_id or ''}|{str(response.critic_passed).lower()}\n\n"
            yield f"event: sources\ndata: {json.dumps([source.model_dump() for source in response.sources], ensure_ascii=True)}\n\n"
            yield f"event: followups\ndata: {json.dumps(response.followups, ensure_ascii=True)}\n\n"
            yield "event: done\ndata: [DONE]\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
