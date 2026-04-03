"""Fully rebuild embedding index from configured source URLs."""
# pyright: reportMissingImports=false

import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.chunker import chunk_text
from app.services.embedder import Embedder
from app.services.ingestion import fetch_page
from app.services.vector_store import IndexedChunk, create_vector_store


async def main() -> None:
    settings = get_settings()
    embedder = Embedder()
    vector_store = create_vector_store(settings=settings, base_dir=str(BACKEND_DIR))
    vector_store.clear()

    chunks: list[IndexedChunk] = []
    for url in settings.source_url_list:
        document = await fetch_page(url)
        split_chunks = list(chunk_text(document.content))

        for index, chunk in enumerate(split_chunks):
            embedding = await embedder.embed_text(chunk)
            chunks.append(
                IndexedChunk(
                    id=f"{document.checksum[:12]}-{index}",
                    title=document.title,
                    url=document.url,
                    snippet=chunk[:240],
                    chunk_text=chunk,
                    embedding=embedding,
                )
            )

    vector_store.upsert_chunks(chunks)
    print(f"Indexed {len(chunks)} chunks")
    print(f"Vector backend: {settings.vector_backend}")


if __name__ == "__main__":
    asyncio.run(main())
