from app.services.chunker import chunk_text


def test_chunk_text_returns_multiple_chunks_for_long_text() -> None:
    text = "word " * 600
    chunks = list(chunk_text(text, chunk_size=200, overlap=50))

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_chunk_text_validates_chunk_size_and_overlap() -> None:
    try:
        list(chunk_text("abc", chunk_size=100, overlap=100))
        raised = False
    except ValueError:
        raised = True

    assert raised
