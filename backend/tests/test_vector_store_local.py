from pathlib import Path

from app.services.vector_store import IndexedChunk, LocalVectorStore


def test_local_vector_store_upsert_and_query(tmp_path: Path) -> None:
    store = LocalVectorStore(str(tmp_path / "index.json"))
    chunk = IndexedChunk(
        id="1",
        title="Doc",
        url="https://example.com",
        snippet="hello",
        chunk_text="hello world",
        embedding=[1.0, 0.0, 0.0],
    )
    store.upsert_chunks([chunk])

    matches = store.query_similar([1.0, 0.0, 0.0], top_k=1)
    assert len(matches) == 1
    assert matches[0].id == "1"


def test_local_vector_store_delete_by_urls(tmp_path: Path) -> None:
    store = LocalVectorStore(str(tmp_path / "index.json"))
    store.save(
        [
            IndexedChunk(
                id="1",
                title="A",
                url="https://a.com",
                snippet="a",
                chunk_text="aaa",
                embedding=[1.0, 0.0],
            ),
            IndexedChunk(
                id="2",
                title="B",
                url="https://b.com",
                snippet="b",
                chunk_text="bbb",
                embedding=[0.0, 1.0],
            ),
        ]
    )

    store.delete_by_urls(["https://a.com"])
    remaining = store.load()
    assert len(remaining) == 1
    assert remaining[0].url == "https://b.com"
