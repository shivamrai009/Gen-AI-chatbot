"""Incrementally sync source pages into vector storage."""
# pyright: reportMissingImports=false

import asyncio
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.entity_extractor import EntityExtractor
from app.services.embedder import Embedder
from app.services.graph_store import GraphStore
from app.services.ingestion import fetch_page
from app.services.markdown_chunker import chunk_markdown_sections
from app.services.sync_state import SyncStateStore
from app.services.vector_store import IndexedChunk, create_vector_store


def chunk_id(checksum: str, index: int) -> str:
    return f"{checksum[:12]}-{index}"


async def main() -> None:
    settings = get_settings()
    embedder = Embedder()
    extractor = EntityExtractor()
    vector_store = create_vector_store(settings=settings, base_dir=str(BACKEND_DIR))
    graph_store = GraphStore(str(BACKEND_DIR / settings.graph_path))
    sync_state = SyncStateStore(str(BACKEND_DIR / "data" / "sync_manifest.json"))

    current_state = sync_state.load()
    discovered_documents = await _discover_documents(settings.source_url_list)
    target_urls = [document.url for document in discovered_documents]

    removed_urls = sorted(set(current_state.keys()) - set(target_urls))
    if removed_urls:
        vector_store.delete_by_urls(removed_urls)
        graph_store.delete_by_urls(removed_urls)
        for url in removed_urls:
            current_state.pop(url, None)

    upserted_chunks = 0
    changed_urls: list[str] = []

    for document in discovered_documents:
        url = document.url
        previous = current_state.get(url)
        if previous and previous.checksum == document.checksum:
            continue

        split_chunks = chunk_markdown_sections(
            sections=[(section.headings, section.text) for section in document.sections]
        )
        rows: list[IndexedChunk] = []
        graph_updates: list[tuple[str, str, str, str, list[str]]] = []
        for index, chunk in enumerate(split_chunks):
            rows.append(
                IndexedChunk(
                    id=chunk_id(document.checksum, index),
                    title=document.title,
                    url=document.url,
                    snippet=chunk.text[:240],
                    chunk_text=chunk.text,
                    embedding=await embedder.embed_text(chunk.text),
                    section_path=chunk.section_path,
                )
            )
            graph_updates.append(
                (
                    document.url,
                    document.title,
                    chunk.text,
                    chunk.section_path,
                    extractor.extract(chunk.text),
                )
            )

        vector_store.delete_by_urls([url])
        graph_store.delete_by_urls([url])
        vector_store.upsert_chunks(rows)
        for graph_update in graph_updates:
            graph_store.upsert_chunk_entities(
                url=graph_update[0],
                title=graph_update[1],
                snippet=graph_update[2],
                section=graph_update[3],
                entities=graph_update[4],
            )
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


async def _discover_documents(seed_urls: list[str]):
    settings = get_settings()
    all_documents = []
    global_seen: set[str] = set()

    for seed_url in seed_urls:
        queue = deque([(seed_url, 0)])
        local_count = 0
        seed_host = urlparse(seed_url).netloc

        while queue and local_count < settings.max_expanded_pages_per_seed:
            url, depth = queue.popleft()
            normalized = url.rstrip("/")
            if normalized in global_seen:
                continue

            try:
                document = await fetch_page(url)
            except Exception:
                continue

            global_seen.add(normalized)
            all_documents.append(document)
            local_count += 1

            if depth >= settings.crawl_depth:
                continue

            child_links = [
                link
                for link in document.internal_links
                if _is_relevant_link(seed_host=seed_host, link=link)
            ]
            for child in child_links[: settings.max_child_links_per_page]:
                if child.rstrip("/") not in global_seen:
                    queue.append((child, depth + 1))

    return all_documents


def _is_relevant_link(seed_host: str, link: str) -> bool:
    parsed = urlparse(link)
    if parsed.netloc != seed_host:
        return False

    if "handbook.gitlab.com" in parsed.netloc:
        return parsed.path.startswith("/handbook") or parsed.path == ""

    return parsed.path.startswith("/company") or parsed.path.startswith("/direction")


if __name__ == "__main__":
    asyncio.run(main())
