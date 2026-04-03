import httpx

from app.core.config import get_settings
from app.models.schemas import Source

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_answer(self, question: str, sources: list[Source]) -> str:
        if not self.settings.gemini_api_key:
            return self._fallback_answer(question, sources)

        prompt = self._build_prompt(question, sources)
        endpoint = (
            f"{GEMINI_API_BASE}/{self.settings.gemini_model}:generateContent"
            f"?key={self.settings.gemini_api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        return self._extract_answer(data)

    def _build_prompt(self, question: str, sources: list[Source]) -> str:
        formatted_sources = "\n\n".join(
            f"Source: {source.title}\nURL: {source.url}\nSnippet: {source.snippet}"
            for source in sources
        )

        return (
            "You are a helpful assistant for GitLab handbook and direction questions. "
            "Only answer using the provided source snippets. If the context is insufficient, "
            "say what is missing and suggest where to look.\n\n"
            f"Question:\n{question}\n\n"
            f"Context:\n{formatted_sources}"
        )

    def _extract_answer(self, payload: dict) -> str:
        try:
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return "I could not generate a reliable answer from the current context."

    def _fallback_answer(self, question: str, sources: list[Source]) -> str:
        source_list = ", ".join(source.title for source in sources)
        return (
            "Gemini API key is not configured. "
            f"Question received: '{question}'. "
            f"Relevant starting sources: {source_list}."
        )
