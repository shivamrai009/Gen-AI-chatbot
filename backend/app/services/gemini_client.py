import httpx
import asyncio

from app.core.config import get_settings
from app.models.schemas import Source

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_API_BASE = "https://api.groq.com/openai/v1/chat/completions"


class GeminiClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_answer(
        self,
        question: str,
        sources: list[Source],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        prompt = self._build_prompt(question, sources)
        if not self.settings.gemini_api_key:
            groq_answer = await self._generate_with_groq(prompt, history)
            if groq_answer:
                return groq_answer
            return self._fallback_answer(question, sources)

        endpoint = (
            f"{GEMINI_API_BASE}/{self.settings.gemini_model}:generateContent"
            f"?key={self.settings.gemini_api_key}"
        )

        # Build multi-turn contents: prior turns + current prompt
        contents: list[dict] = []
        for turn in (history or []):
            role = turn.get("role", "user")
            # Gemini uses "model" for assistant turns
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": turn.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {"contents": contents}

        retries = 2
        backoff_seconds = 1.0
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    data = response.json()
                return self._extract_answer(data)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code in {429, 500, 502, 503, 504} and attempt < retries:
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds *= 2
                    continue
                groq_answer = await self._generate_with_groq(prompt, history)
                if groq_answer:
                    return groq_answer
                return self._fallback_answer(question, sources)
            except httpx.HTTPError:
                if attempt < retries:
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds *= 2
                    continue
                groq_answer = await self._generate_with_groq(prompt, history)
                if groq_answer:
                    return groq_answer
                return self._fallback_answer(question, sources)

        groq_answer = await self._generate_with_groq(prompt, history)
        if groq_answer:
            return groq_answer
        return self._fallback_answer(question, sources)

    async def _generate_with_groq(
        self, prompt: str, history: list[dict[str, str]] | None = None
    ) -> str | None:
        if not self.settings.groq_api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": "You are a helpful assistant focused on GitLab handbook and direction knowledge.",
            }
        ]
        # Inject prior turns so Groq has full conversation context
        for turn in (history or []):
            role = turn.get("role", "user")
            if role in {"user", "assistant"}:
                messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.settings.groq_model,
            "messages": messages,
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(GROQ_API_BASE, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None

        try:
            content = data["choices"][0]["message"]["content"]
            return str(content).strip() if content else None
        except (KeyError, IndexError, TypeError):
            return None

    def _build_prompt(self, question: str, sources: list[Source]) -> str:
        formatted_sources = "\n\n---\n\n".join(
            f"Source: {source.title}\nURL: {source.url}\nContent: {source.snippet}"
            for source in sources
        )

        return (
            "You are a knowledgeable assistant for GitLab handbook and direction questions. "
            "Use the provided source content to give a clear, direct, and helpful answer. "
            "Synthesize information across sources — do not just quote them. "
            "If the sources contain partial information, use it fully and note what additional sections might help. "
            "Never say the context is empty or missing when sources are provided — always extract the most useful answer you can.\n\n"
            f"Question:\n{question}\n\n"
            f"Source Content:\n{formatted_sources}"
        )

    def _extract_answer(self, payload: dict) -> str:
        try:
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return "I could not generate a reliable answer from the current context."

    async def generate_followups(self, question: str, answer: str) -> list[str]:
        """Return 3 short follow-up questions the user might ask next."""
        import json, re

        prompt = (
            "Given this Q&A about GitLab, suggest exactly 3 short follow-up questions "
            "a user might ask next. Return ONLY a valid JSON array of 3 strings, "
            "no explanation, no markdown code fences, no numbering.\n\n"
            f"Q: {question}\nA: {answer[:600]}\n\n"
            'Example output: ["What is X?", "How does Y work?", "Where can I find Z?"]'
        )

        def _parse_followups(text: str) -> list[str]:
            """Extract JSON array from model text, tolerating code fences."""
            text = text.strip()
            # Try direct parse first
            try:
                result = json.loads(text)
                if isinstance(result, list):
                    return [q for q in result if isinstance(q, str)][:3]
            except json.JSONDecodeError:
                pass
            # Strip code fences and try again
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
            try:
                result = json.loads(text)
                if isinstance(result, list):
                    return [q for q in result if isinstance(q, str)][:3]
            except json.JSONDecodeError:
                pass
            # Last resort: extract anything that looks like a JSON array
            match = re.search(r"\[[\s\S]*?\]", text)
            if match:
                try:
                    result = json.loads(match.group())
                    if isinstance(result, list):
                        return [q for q in result if isinstance(q, str)][:3]
                except json.JSONDecodeError:
                    pass
            return []

        # Try Gemini first
        if self.settings.gemini_api_key:
            endpoint = (
                f"{GEMINI_API_BASE}/{self.settings.gemini_model}:generateContent"
                f"?key={self.settings.gemini_api_key}"
            )
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    text = self._extract_answer(response.json())
                    questions = _parse_followups(text)
                    if questions:
                        return questions
                    print(f"[followups] Gemini returned unparseable text: {text[:200]!r}")
            except httpx.HTTPStatusError as exc:
                print(f"[followups] Gemini HTTP {exc.response.status_code}, trying Groq fallback")
            except Exception as exc:
                print(f"[followups] Gemini error: {exc}, trying Groq fallback")

        # Groq fallback
        if self.settings.groq_api_key:
            headers = {
                "Authorization": f"Bearer {self.settings.groq_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.settings.groq_model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Return only valid JSON arrays."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(GROQ_API_BASE, headers=headers, json=payload)
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    questions = _parse_followups(content)
                    if questions:
                        return questions
                    print(f"[followups] Groq returned unparseable text: {content[:200]!r}")
            except Exception as exc:
                print(f"[followups] Groq error: {exc}")

        print("[followups] All providers failed, returning []")
        return []

    def _fallback_answer(self, question: str, sources: list[Source]) -> str:
        source_list = ", ".join(source.title for source in sources)
        return (
            "Gemini API key is not configured. "
            f"Question received: '{question}'. "
            f"Relevant starting sources: {source_list}."
        )
