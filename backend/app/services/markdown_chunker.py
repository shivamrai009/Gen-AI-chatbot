from dataclasses import dataclass


@dataclass
class HierarchicalChunk:
    text: str
    section_path: str


def chunk_markdown_sections(
    sections: list[tuple[list[str], str]],
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[HierarchicalChunk]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")

    chunks: list[HierarchicalChunk] = []
    for headings, text in sections:
        normalized = " ".join(text.split())
        if not normalized:
            continue

        section_path = " > ".join([item.strip() for item in headings if item and item.strip()])
        if not section_path:
            section_path = "General"

        start = 0
        total = len(normalized)
        while start < total:
            end = min(start + chunk_size, total)
            chunks.append(HierarchicalChunk(text=normalized[start:end], section_path=section_path))
            if end == total:
                break
            start = end - overlap

    return chunks
