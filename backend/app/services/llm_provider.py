from app.models.schemas import Source
from app.services.gemini_client import GeminiClient


class LLMProvider:
    def __init__(self) -> None:
        self.gemini = GeminiClient()

    async def generate(
        self,
        question: str,
        sources: list[Source],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        return await self.gemini.generate_answer(question, sources, history)

    async def generate_followups(self, question: str, answer: str) -> list[str]:
        return await self.gemini.generate_followups(question, answer)
