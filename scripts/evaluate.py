"""Run lightweight retrieval/answer quality checks against a fixed question set."""
# pyright: reportMissingImports=false

import asyncio
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.config import get_settings
from app.models.schemas import ChatRequest
from app.services.critic import CriticService
from app.services.embedder import Embedder
from app.services.entity_extractor import EntityExtractor
from app.services.graph_retriever import GraphRetriever
from app.services.graph_store import GraphStore
from app.services.guardrails import GuardrailService
from app.services.llm_provider import LLMProvider
from app.services.orchestrator import ChatOrchestrator
from app.services.retriever import VectorRetriever
from app.services.router import RouterService
from app.services.telemetry import TelemetryService
from app.services.vector_store import create_vector_store


async def main() -> None:
    settings = get_settings()
    dataset = json.loads((ROOT_DIR / "eval" / "questions.json").read_text(encoding="utf-8"))
    retriever = VectorRetriever(
        Embedder(),
        create_vector_store(settings=settings, base_dir=str(BACKEND_DIR)),
        graph_retriever=GraphRetriever(EntityExtractor(), GraphStore(str(BACKEND_DIR / settings.graph_path))),
    )
    orchestrator = ChatOrchestrator(
        router=RouterService(),
        retriever=retriever,
        provider=LLMProvider(),
        critic=CriticService(),
        guardrails=GuardrailService(),
        telemetry=TelemetryService(str(BACKEND_DIR / "data" / "eval_telemetry.log")),
    )

    total = len(dataset)
    citation_pass = 0
    keyword_pass = 0
    route_pass = 0
    guardrail_pass = 0
    critic_pass = 0

    for item in dataset:
        question = item["question"]
        expected_keywords = [word.lower() for word in item.get("expected_keywords", [])]
        expected_route = item.get("expected_route")

        result = await orchestrator.run(ChatRequest(question=question, history=[]))
        sources = result.sources
        answer = result.answer

        has_sources = len(sources) > 0
        if has_sources:
            citation_pass += 1

        if result.critic_passed:
            critic_pass += 1

        if expected_route and result.route == expected_route:
            route_pass += 1

        if expected_route == "reject":
            if result.route == "reject":
                guardrail_pass += 1
        else:
            guardrail_pass += 1

        lowered = answer.lower()
        keyword_hits = sum(1 for keyword in expected_keywords if keyword in lowered)
        if not expected_keywords:
            keyword_pass += 1
        elif keyword_hits >= max(1, len(expected_keywords) // 2):
            keyword_pass += 1

        print(f"[{item['id']}] {question}")
        print(f"- route: {result.route} (expected: {expected_route})")
        print(f"- sources: {len(sources)}")
        print(f"- keyword hits: {keyword_hits}/{len(expected_keywords)}")
        print(f"- critic passed: {result.critic_passed}")

    citation_score = (citation_pass / total) * 100 if total else 0
    keyword_score = (keyword_pass / total) * 100 if total else 0
    route_score = (route_pass / total) * 100 if total else 0
    guardrail_score = (guardrail_pass / total) * 100 if total else 0
    critic_score = (critic_pass / total) * 100 if total else 0

    print("\nEvaluation summary")
    print(f"- Total questions: {total}")
    print(f"- Citation coverage: {citation_score:.1f}%")
    print(f"- Keyword adequacy: {keyword_score:.1f}%")
    print(f"- Route accuracy: {route_score:.1f}%")
    print(f"- Guardrail handling: {guardrail_score:.1f}%")
    print(f"- Critic pass rate: {critic_score:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
