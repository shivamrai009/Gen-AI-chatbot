from time import perf_counter
from uuid import uuid4

from app.core.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse, Source
from app.services.critic import CriticService
from app.services.guardrails import GuardrailService
from app.services.llm_provider import LLMProvider
from app.services.retriever import VectorRetriever
from app.services.router import RouterService
from app.services.telemetry import TelemetryService


class ChatOrchestrator:
    def __init__(
        self,
        router: RouterService,
        retriever: VectorRetriever,
        provider: LLMProvider,
        critic: CriticService,
        guardrails: GuardrailService,
        telemetry: TelemetryService,
    ) -> None:
        self.router = router
        self.retriever = retriever
        self.provider = provider
        self.critic = critic
        self.guardrails = guardrails
        self.telemetry = telemetry
        self.settings = get_settings()

    async def run(self, request: ChatRequest) -> ChatResponse:
        trace_id = str(uuid4())
        total_start = perf_counter()

        guard_start = perf_counter()
        guardrail = self.guardrails.check(request.question)
        self.telemetry.log(
            trace_id,
            "guardrails",
            {"blocked": guardrail.blocked, "reason": guardrail.reason},
            elapsed_ms=(perf_counter() - guard_start) * 1000,
        )
        if guardrail.blocked:
            response = ChatResponse(
                answer=guardrail.response or "Request blocked by guardrails.",
                sources=[],
                model=self.settings.gemini_model,
                route="reject",
                confidence=1.0,
                trace_id=trace_id,
                critic_passed=True,
            )
            self.telemetry.log(
                trace_id,
                "final",
                {"route": response.route, "blocked": True},
                elapsed_ms=(perf_counter() - total_start) * 1000,
            )
            return response

        route_start = perf_counter()
        decision = self.router.decide(request.question)
        self.telemetry.log(
            trace_id,
            "route",
            {"route": decision.route, "confidence": decision.confidence, "reason": decision.reason},
            elapsed_ms=(perf_counter() - route_start) * 1000,
        )

        if decision.route == "reject":
            response = ChatResponse(
                answer=(
                    "I can help with GitLab Handbook and Direction topics only. "
                    "Please ask a question related to GitLab processes, strategy, teams, or documentation."
                ),
                sources=[],
                model=self.settings.gemini_model,
                route=decision.route,
                confidence=decision.confidence,
                trace_id=trace_id,
                critic_passed=True,
            )
            self.telemetry.log(
                trace_id,
                "final",
                {"route": response.route, "blocked": True},
                elapsed_ms=(perf_counter() - total_start) * 1000,
            )
            return response

        if decision.route == "clarify":
            response = ChatResponse(
                answer=(
                    "Could you add a bit more detail so I can retrieve the right handbook or direction context? "
                    "For example, include the team, process, or objective you mean."
                ),
                sources=[],
                model=self.settings.gemini_model,
                route=decision.route,
                confidence=decision.confidence,
                trace_id=trace_id,
                critic_passed=True,
            )
            self.telemetry.log(
                trace_id,
                "final",
                {"route": response.route, "blocked": False},
                elapsed_ms=(perf_counter() - total_start) * 1000,
            )
            return response

        retrieval_mode = decision.route if decision.route in {"vector", "graph", "hybrid"} else "hybrid"
        retrieve_start = perf_counter()
        sources = await self.retriever.search_with_mode(
            request.question,
            top_k=self.settings.max_context_chunks,
            mode=retrieval_mode,
        )
        self.telemetry.log(
            trace_id,
            "retrieve",
            {"mode": retrieval_mode, "source_count": len(sources)},
            elapsed_ms=(perf_counter() - retrieve_start) * 1000,
        )

        generate_start = perf_counter()
        answer = await self.provider.generate(request.question, sources, request.history)
        self.telemetry.log(
            trace_id,
            "generate",
            {"answer_chars": len(answer)},
            elapsed_ms=(perf_counter() - generate_start) * 1000,
        )

        critic_start = perf_counter()
        critic_result = self.critic.evaluate(answer, sources)
        attempts = 0
        while (not critic_result.passed) and attempts < self.settings.max_regeneration_attempts:
            attempts += 1
            retry_question = (
                "Answer strictly from the provided context and avoid unsupported claims. "
                f"Original question: {request.question}"
            )
            answer = await self.provider.generate(retry_question, sources, request.history)
            critic_result = self.critic.evaluate(answer, sources)
        self.telemetry.log(
            trace_id,
            "critic",
            {"passed": critic_result.passed, "reason": critic_result.reason, "attempts": attempts},
            elapsed_ms=(perf_counter() - critic_start) * 1000,
        )

        # Generate follow-up suggestions in parallel with finalising the response
        followups = await self.provider.generate_followups(request.question, answer)

        response = ChatResponse(
            answer=answer,
            sources=sources,
            model=self.settings.gemini_model,
            route=decision.route,
            confidence=decision.confidence,
            trace_id=trace_id,
            critic_passed=critic_result.passed,
            followups=followups,
        )
        self.telemetry.log(
            trace_id,
            "final",
            {"route": response.route, "critic_passed": response.critic_passed},
            elapsed_ms=(perf_counter() - total_start) * 1000,
        )
        return response
