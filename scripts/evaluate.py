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
from app.services.embedder import Embedder
from app.services.gemini_client import GeminiClient
from app.services.retriever import VectorRetriever
from app.services.vector_store import create_vector_store


async def main() -> None:
    settings = get_settings()
    dataset = json.loads((ROOT_DIR / "eval" / "questions.json").read_text(encoding="utf-8"))
    retriever = VectorRetriever(Embedder(), create_vector_store(settings=settings, base_dir=str(BACKEND_DIR)))
    generator = GeminiClient()

    total = len(dataset)
    citation_pass = 0
    keyword_pass = 0

    for item in dataset:
        question = item["question"]
        expected_keywords = [word.lower() for word in item.get("expected_keywords", [])]

        sources = await retriever.search(question, top_k=settings.max_context_chunks)
        answer = await generator.generate_answer(question, sources)

        has_sources = len(sources) > 0
        if has_sources:
            citation_pass += 1

        lowered = answer.lower()
        keyword_hits = sum(1 for keyword in expected_keywords if keyword in lowered)
        if expected_keywords and keyword_hits >= max(1, len(expected_keywords) // 2):
            keyword_pass += 1

        print(f"[{item['id']}] {question}")
        print(f"- sources: {len(sources)}")
        print(f"- keyword hits: {keyword_hits}/{len(expected_keywords)}")

    citation_score = (citation_pass / total) * 100 if total else 0
    keyword_score = (keyword_pass / total) * 100 if total else 0

    print("\nEvaluation summary")
    print(f"- Total questions: {total}")
    print(f"- Citation coverage: {citation_score:.1f}%")
    print(f"- Keyword adequacy: {keyword_score:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
