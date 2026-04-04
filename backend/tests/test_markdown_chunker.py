from app.services.markdown_chunker import chunk_markdown_sections


def test_chunk_markdown_sections_preserves_section_path() -> None:
    sections = [(["Root", "Sub"], "hello world " * 100)]
    chunks = chunk_markdown_sections(sections, chunk_size=120, overlap=20)

    assert len(chunks) > 1
    assert all(chunk.section_path == "Root > Sub" for chunk in chunks)


def test_chunk_markdown_sections_rejects_invalid_sizes() -> None:
    try:
        chunk_markdown_sections([(["A"], "text")], chunk_size=100, overlap=100)
        raised = False
    except ValueError:
        raised = True

    assert raised
