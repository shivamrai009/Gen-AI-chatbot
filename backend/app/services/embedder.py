import hashlib

import httpx

from app.core.config import get_settings

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class Embedder:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def embed_text(self, text: str) -> list[float]:
        if not self.settings.gemini_api_key:
            return self._hash_embedding(text)

        endpoint = (
            f"{GEMINI_API_BASE}/{self.settings.gemini_embedding_model}:embedContent"
            f"?key={self.settings.gemini_api_key}"
        )
        payload = {
            "model": f"models/{self.settings.gemini_embedding_model}",
            "content": {"parts": [{"text": text}]},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        values = data.get("embedding", {}).get("values", [])
        if not values:
            return self._hash_embedding(text)
        return [float(value) for value in values]

    def _hash_embedding(self, text: str) -> list[float]:
        """Deterministic fallback embedding for local development without an API key."""
        dims = self.settings.embedding_dimensions
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = [0.0] * dims

        for index, byte in enumerate(digest):
            slot = index % dims
            vector[slot] += (byte / 255.0) - 0.5

        return vector
