"""Fully rebuild embedding index from configured source URLs."""
# pyright: reportMissingImports=false

import asyncio
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

EMBED_CONCURRENCY = 10  # parallel embedding calls per page

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
from app.services.vector_store import IndexedChunk, create_vector_store


async def main() -> None:
    settings = get_settings()
    embedder = Embedder()
    extractor = EntityExtractor()
    vector_store = create_vector_store(settings=settings, base_dir=str(BACKEND_DIR))
    graph_store = GraphStore(str(BACKEND_DIR / settings.graph_path))
    vector_store.clear()
    graph_store.clear()

    chunks: list[IndexedChunk] = []
    graph_rows = 0
    discovered_documents = await _discover_documents(settings.source_url_list)
    semaphore = asyncio.Semaphore(EMBED_CONCURRENCY)

    async def embed_chunk(document, index, chunk):
        async with semaphore:
            embedding = await embedder.embed_text(chunk.text)
        return IndexedChunk(
            id=f"{document.checksum[:12]}-{index}",
            title=document.title,
            url=document.url,
            snippet=chunk.text[:240],
            chunk_text=chunk.text,
            embedding=embedding,
            section_path=chunk.section_path,
        )

    for document in discovered_documents:
        split_chunks = chunk_markdown_sections(
            sections=[(section.headings, section.text) for section in document.sections]
        )
        print(f"  Embedding {len(split_chunks)} chunks from {document.url} ...")

        # Embed all chunks for this document in parallel (bounded by semaphore)
        indexed = await asyncio.gather(*[
            embed_chunk(document, i, chunk) for i, chunk in enumerate(split_chunks)
        ])
        chunks.extend(indexed)

        for chunk in split_chunks:
            entities = extractor.extract(chunk.text)
            graph_store.upsert_chunk_entities(
                url=document.url,
                title=document.title,
                snippet=chunk.text,
                section=chunk.section_path,
                entities=entities,
            )
            graph_rows += 1

    vector_store.upsert_chunks(chunks)
    print(f"Indexed {len(chunks)} chunks")
    print(f"Graph records processed: {graph_rows}")
    print(f"Discovered pages: {len(discovered_documents)}")
    print(f"Vector backend: {settings.vector_backend}")


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

            if _is_blocked_url(urlparse(url).path):
                global_seen.add(normalized)
                continue

            try:
                document = await fetch_page(url)
            except Exception:
                continue

            # Skip if the final URL (after redirects) is a blocked path
            if _is_blocked_url(urlparse(document.url).path):
                global_seen.add(normalized)
                global_seen.add(document.url.rstrip("/"))
                print(f"  Skipped (blocked after redirect): {document.url}")
                continue

            global_seen.add(normalized)
            global_seen.add(document.url.rstrip("/"))
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


# URL path segments that produce low-quality, noisy index content
_BLOCKED_PATH_SEGMENTS = {
    "/company/team",    # thousands of individual team member bios
    "/releases",        # release changelogs, not handbook guidance
    "/company/contact", # contact forms
    "/press",           # press releases
    "/blog",            # blog posts (out of scope)
    "/events",          # event listings
    "/jobs",            # job listings
    "/pricing",         # pricing pages
}


def _is_blocked_url(path: str) -> bool:
    return any(path.startswith(seg) for seg in _BLOCKED_PATH_SEGMENTS)


def _is_relevant_link(seed_host: str, link: str) -> bool:
    parsed = urlparse(link)
    if parsed.netloc != seed_host:
        return False

    if _is_blocked_url(parsed.path):
        return False

    if "handbook.gitlab.com" in parsed.netloc:
        return parsed.path.startswith("/handbook") or parsed.path == ""

    # Keep non-handbook domains conservative to avoid indexing broad marketing pages.
    return parsed.path.startswith("/company") or parsed.path.startswith("/direction")


if __name__ == "__main__":
    asyncio.run(main())
