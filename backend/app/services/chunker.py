from collections.abc import Iterator


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> Iterator[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")

    normalized = " ".join(text.split())
    start = 0
    total = len(normalized)

    while start < total:
        end = min(start + chunk_size, total)
        yield normalized[start:end]
        if end == total:
            break
        start = end - overlap
