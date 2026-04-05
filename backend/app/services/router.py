from dataclasses import dataclass


@dataclass
class RouteDecision:
    route: str
    confidence: float
    reason: str



class RouterService:
    OFF_TOPIC_TERMS = {
        "python script",
        "write code",
        "weather",
        "movie",
        "football",
        "recipe",
        "crypto",
    }

    GRAPH_HINT_TERMS = {
        "connect",
        "relationship",
        "impact",
        "between",
        "dependency",
        "tradeoff",
        "owner",
        "responsible",
    }

    # Generic filler phrases that carry no retrieval signal on their own
    VAGUE_PATTERNS = {
        "tell me something",
        "tell me more",
        "tell me",
        "what do you know",
        "what can you tell",
        "just ask",
        "i don't know",
        "anything",
        "something",
        "go on",
        "keep going",
    }

    def decide(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> RouteDecision:
        lowered = question.lower().strip()
        words = lowered.split()

        # ── If there is conversation history, never send short replies to "clarify" ──
        # The user is continuing the conversation, not asking a standalone question.
        if history and len(words) <= 4:
            return RouteDecision(
                route="vector",
                confidence=0.75,
                reason="Short contextual reply with active conversation history",
            )

        # ── Standalone short or vague query with no history → ask for more detail ──
        if len(words) <= 2 or any(p in lowered for p in self.VAGUE_PATTERNS):
            return RouteDecision(route="clarify", confidence=0.8, reason="Query too short or vague")

        if any(term in lowered for term in self.OFF_TOPIC_TERMS):
            return RouteDecision(route="reject", confidence=0.95, reason="Out-of-domain request")

        if any(term in lowered for term in self.GRAPH_HINT_TERMS):
            return RouteDecision(route="hybrid", confidence=0.8, reason="Likely relational question")

        if "who" in lowered and ("team" in lowered or "owner" in lowered):
            return RouteDecision(route="graph", confidence=0.7, reason="Entity ownership style query")

        return RouteDecision(route="vector", confidence=0.65, reason="Default semantic retrieval")
