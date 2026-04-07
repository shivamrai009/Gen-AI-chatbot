from app.core.config import get_settings
from app.models.schemas import Source
from app.services.embedder import Embedder
from app.services.graph_retriever import GraphRetriever
from app.services.vector_store import IndexedChunk, LocalVectorStore, PgVectorStore


class VectorRetriever:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: LocalVectorStore | PgVectorStore,
        graph_retriever: GraphRetriever | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.graph_retriever = graph_retriever
        self.settings = get_settings()

    async def search(self, question: str, top_k: int = 4) -> list[Source]:
        return await self.search_with_mode(question=question, top_k=top_k, mode="hybrid")

    async def search_with_mode(self, question: str, top_k: int = 4, mode: str = "hybrid") -> list[Source]:
        vector_sources: list[Source] = []
        if mode in {"vector", "hybrid"}:
            vector_sources = await self._search_vector_sources(question, top_k=top_k)

        graph_sources: list[Source] = []
        if self.graph_retriever is not None and mode in {"graph", "hybrid"}:
            graph_sources = self.graph_retriever.search(question, top_k=max(top_k, 6))

        if mode == "vector":
            merged = self._enforce_url_diversity(vector_sources, top_k=top_k)
        elif mode == "graph":
            merged = self._enforce_url_diversity(graph_sources, top_k=top_k)
        else:
            merged = self._merge_sources(vector_sources, graph_sources, top_k=top_k)

        if not merged:
            return [
                Source(
                    title="Indexer not built yet",
                    url="https://handbook.gitlab.com",
                    snippet="Run scripts/build_index.py to build a local vector index.",
                )
            ]
        return merged

    def _to_source(self, chunk: IndexedChunk) -> Source:
        return Source(
            title=chunk.title,
            url=chunk.url,
            snippet=chunk.chunk_text or chunk.snippet,
            section=chunk.section_path,
        )

    def _merge_sources(self, vector_sources: list[Source], graph_sources: list[Source], top_k: int) -> list[Source]:
        score_map: dict[tuple[str, str], float] = {}
        source_map: dict[tuple[str, str], Source] = {}

        for index, source in enumerate(vector_sources):
            key = (source.url, source.snippet)
            source_map[key] = source
            score_map[key] = score_map.get(key, 0.0) + self.settings.hybrid_vector_weight * (1.0 / (index + 1))

        for index, source in enumerate(graph_sources):
            key = (source.url, source.snippet)
            source_map[key] = source
            score_map[key] = score_map.get(key, 0.0) + self.settings.hybrid_graph_weight * (1.0 / (index + 1))

        ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        ranked_sources = [source_map[key] for key, _ in ranked]
        return self._enforce_url_diversity(ranked_sources, top_k=top_k)

    async def _search_vector_sources(self, question: str, top_k: int) -> list[Source]:
        queries = self._expand_queries(question)
        ranked_sources: list[Source] = []
        seen_keys: set[tuple[str, str]] = set()

        for query_index, query in enumerate(queries):
            query_vector = await self.embedder.embed_text(query)
            chunks = self.vector_store.query_similar(query_vector, max(top_k * 2, 8))
            for rank_index, chunk in enumerate(chunks):
                source = self._to_source(chunk)
                key = (source.url, source.snippet)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                # Weighted insertion by query priority and local rank.
                insertion_index = min(len(ranked_sources), (query_index * 2) + rank_index)
                ranked_sources.insert(insertion_index, source)

        return self._enforce_url_diversity(ranked_sources, top_k=max(top_k, 8))

    def _expand_queries(self, question: str) -> list[str]:
        lowered = question.lower()
        queries = [question]

        if "deployment" in lowered:
            queries.append(f"{question} release strategy CI CD")
        if "marketing" in lowered:
            queries.append(f"{question} marketing objectives campaign launch")
        if "connect" in lowered or "relationship" in lowered or "impact" in lowered:
            queries.append(f"{question} cross-functional alignment engineering marketing")

        seen: set[str] = set()
        unique_queries: list[str] = []
        for query in queries:
            normalized = query.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_queries.append(normalized)
        return unique_queries

    def _enforce_url_diversity(self, sources: list[Source], top_k: int) -> list[Source]:
        unique_urls: set[str] = set()
        selected: list[Source] = []
        overflow: list[Source] = []

        for source in sources:
            if source.url not in unique_urls:
                unique_urls.add(source.url)
                selected.append(source)
            else:
                overflow.append(source)

        combined = selected + overflow
        return combined[:top_k]
