import hashlib
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass
class PageDocument:
    url: str
    title: str
    content: str
    checksum: str


def build_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def fetch_page(url: str) -> PageDocument:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    title = soup.title.text.strip() if soup.title else url
    content = " ".join(soup.get_text(" ").split())

    return PageDocument(
        url=str(response.url),
        title=title,
        content=content,
        checksum=build_checksum(content),
    )
