import hashlib
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class PageSection:
    headings: list[str]
    text: str


@dataclass
class PageDocument:
    url: str
    title: str
    content: str
    checksum: str
    sections: list[PageSection]
    internal_links: list[str]


def build_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def fetch_page(url: str) -> PageDocument:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    title = soup.title.text.strip() if soup.title else url
    content = " ".join(soup.get_text(" ").split())
    sections = _extract_sections(soup, title, content)
    internal_links = _extract_internal_links(soup, str(response.url))

    return PageDocument(
        url=str(response.url),
        title=title,
        content=content,
        checksum=build_checksum(content),
        sections=sections,
        internal_links=internal_links,
    )


_SKIP_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript"}


def _main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """Return the most specific content container, falling back to <body>."""
    for selector in ("main", "article", '[role="main"]', ".content", "#content", "body"):
        node = soup.select_one(selector)
        if node:
            # Remove noisy non-content subtrees in-place
            for skip in node.find_all(_SKIP_TAGS):
                skip.decompose()
            return node
    return soup


def _extract_sections(soup: BeautifulSoup, title: str, fallback_content: str) -> list[PageSection]:
    content_root = _main_content(soup)
    sections: list[PageSection] = []
    current = {"h1": title, "h2": "", "h3": ""}

    for node in content_root.find_all(["h1", "h2", "h3", "p", "li"]):
        text = " ".join(node.get_text(" ").split())
        if not text:
            continue

        node_name = node.name.lower()
        if node_name in {"h1", "h2", "h3"}:
            current[node_name] = text
            if node_name == "h1":
                current["h2"] = ""
                current["h3"] = ""
            elif node_name == "h2":
                current["h3"] = ""
            continue

        if len(text) < 40:
            continue

        headings = [current["h1"], current["h2"], current["h3"]]
        sections.append(PageSection(headings=[value for value in headings if value], text=text))

    if sections:
        return sections

    return [PageSection(headings=[title], text=fallback_content)]


def _extract_internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    parsed_base = urlparse(base_url)
    host = parsed_base.netloc

    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("#"):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc != host:
            continue

        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))
        if normalized == base_url.rstrip("/"):
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        links.append(normalized)

    return links
