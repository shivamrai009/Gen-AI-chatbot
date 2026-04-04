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

    def decide(self, question: str) -> RouteDecision:
        lowered = question.lower().strip()

        if len(lowered.split()) <= 2:
            return RouteDecision(route="clarify", confidence=0.8, reason="Query too short")

        if any(term in lowered for term in self.OFF_TOPIC_TERMS):
            return RouteDecision(route="reject", confidence=0.95, reason="Out-of-domain request")

        if any(term in lowered for term in self.GRAPH_HINT_TERMS):
            return RouteDecision(route="hybrid", confidence=0.8, reason="Likely relational question")

        if "who" in lowered and ("team" in lowered or "owner" in lowered):
            return RouteDecision(route="graph", confidence=0.7, reason="Entity ownership style query")

        return RouteDecision(route="vector", confidence=0.65, reason="Default semantic retrieval")
