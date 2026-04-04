from pathlib import Path

from app.services.graph_store import GraphStore


def test_graph_store_upsert_and_query(tmp_path: Path) -> None:
    store = GraphStore(str(tmp_path / "graph.json"))
    store.clear()

    store.upsert_chunk_entities(
        url="https://example.com/one",
        title="Doc One",
        snippet="Engineering deployment strategy aligns with Product goals.",
        section="Strategy",
        entities=["Engineering", "Product", "Strategy"],
    )

    store.upsert_chunk_entities(
        url="https://example.com/two",
        title="Doc Two",
        snippet="Marketing and Product plans for Q3.",
        section="Planning",
        entities=["Marketing", "Product", "Q3"],
    )

    results = store.query(["Product"], top_k=2)
    assert len(results) >= 1
    assert results[0].url.startswith("https://example.com")


def test_graph_store_delete_by_urls(tmp_path: Path) -> None:
    store = GraphStore(str(tmp_path / "graph.json"))
    store.clear()
    store.upsert_chunk_entities(
        url="https://example.com/remove",
        title="Doc",
        snippet="Snippet",
        section="General",
        entities=["EntityA", "EntityB"],
    )

    store.delete_by_urls(["https://example.com/remove"])
    results = store.query(["EntityA"], top_k=2)
    assert results == []
