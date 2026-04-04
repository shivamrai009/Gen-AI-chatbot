from dataclasses import dataclass

from app.models.schemas import Source


@dataclass
class CriticResult:
    passed: bool
    reason: str


class CriticService:
    def evaluate(self, answer: str, sources: list[Source]) -> CriticResult:
        if not answer.strip():
            return CriticResult(passed=False, reason="Empty answer")

        if "api key is not configured" in answer.lower():
            return CriticResult(passed=True, reason="Fallback mode")

        if not sources:
            return CriticResult(passed=False, reason="No retrieved sources")

        answer_terms = set(self._normalize(answer))
        source_terms: set[str] = set()
        for source in sources:
            source_terms.update(self._normalize(source.snippet))
            source_terms.update(self._normalize(source.title))

        if not answer_terms:
            return CriticResult(passed=False, reason="Answer has no lexical signal")

        overlap = len(answer_terms.intersection(source_terms)) / max(1, len(answer_terms))
        if overlap < 0.08:
            return CriticResult(passed=False, reason="Low grounding overlap")

        return CriticResult(passed=True, reason="Grounded by retrieved evidence")

    def _normalize(self, text: str) -> list[str]:
        cleaned = "".join(char.lower() if char.isalnum() else " " for char in text)
        return [token for token in cleaned.split() if len(token) > 2]
