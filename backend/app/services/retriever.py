from app.models.schemas import Source
from app.services.embedder import Embedder
from app.services.vector_store import IndexedChunk, LocalVectorStore, PgVectorStore


class VectorRetriever:
    def __init__(self, embedder: Embedder, vector_store: LocalVectorStore | PgVectorStore) -> None:
        self.embedder = embedder
        self.vector_store = vector_store

    async def search(self, question: str, top_k: int = 4) -> list[Source]:
        query_vector = await self.embedder.embed_text(question)
        chunks = self.vector_store.query_similar(query_vector, top_k)
        if not chunks:
            return [
                Source(
                    title="Indexer not built yet",
                    url="https://handbook.gitlab.com",
                    snippet="Run scripts/build_index.py to build a local vector index.",
                )
            ]
        return [self._to_source(chunk) for chunk in chunks]

    def _to_source(self, chunk: IndexedChunk) -> Source:
        return Source(title=chunk.title, url=chunk.url, snippet=chunk.snippet)
