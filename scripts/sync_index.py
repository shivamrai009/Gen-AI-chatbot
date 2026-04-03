"""Incrementally sync source pages into vector storage."""
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
from app.services.sync_state import SyncStateStore
from app.services.vector_store import IndexedChunk, create_vector_store


def chunk_id(checksum: str, index: int) -> str:
    return f"{checksum[:12]}-{index}"


async def main() -> None:
    settings = get_settings()
    embedder = Embedder()
    vector_store = create_vector_store(settings=settings, base_dir=str(BACKEND_DIR))
    sync_state = SyncStateStore(str(BACKEND_DIR / "data" / "sync_manifest.json"))

    current_state = sync_state.load()
    target_urls = settings.source_url_list

    removed_urls = sorted(set(current_state.keys()) - set(target_urls))
    if removed_urls:
        vector_store.delete_by_urls(removed_urls)
        for url in removed_urls:
            current_state.pop(url, None)

    upserted_chunks = 0
    changed_urls: list[str] = []

    for url in target_urls:
        document = await fetch_page(url)
        previous = current_state.get(url)
        if previous and previous.checksum == document.checksum:
            continue

        split_chunks = list(chunk_text(document.content))
        rows: list[IndexedChunk] = []
        for index, chunk in enumerate(split_chunks):
            rows.append(
                IndexedChunk(
                    id=chunk_id(document.checksum, index),
                    title=document.title,
                    url=document.url,
                    snippet=chunk[:240],
                    chunk_text=chunk,
                    embedding=await embedder.embed_text(chunk),
                )
            )

        vector_store.delete_by_urls([url])
        vector_store.upsert_chunks(rows)
        current_state[url] = sync_state.stamp(url=url, checksum=document.checksum)
        changed_urls.append(url)
        upserted_chunks += len(rows)

    sync_state.save(current_state)
    print(f"Changed URLs: {len(changed_urls)}")
    print(f"Upserted chunks: {upserted_chunks}")
    if changed_urls:
        print("Updated sources:")
        for url in changed_urls:
            print(f"- {url}")


if __name__ == "__main__":
    asyncio.run(main())
