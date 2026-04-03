"""Quick bootstrap script to fetch a few GitLab pages and print chunk stats."""
# pyright: reportMissingImports=false

import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.services.chunker import chunk_text
from app.core.config import get_settings
from app.services.ingestion import fetch_page


async def main() -> None:
    settings = get_settings()
    for url in settings.source_url_list:
        document = await fetch_page(url)
        chunks = list(chunk_text(document.content))
        print(f"URL: {document.url}")
        print(f"Title: {document.title}")
        print(f"Checksum: {document.checksum[:12]}...")
        print(f"Chunks: {len(chunks)}")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
