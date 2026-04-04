from app.models.schemas import Source
from app.services.entity_extractor import EntityExtractor
from app.services.graph_store import GraphStore


class GraphRetriever:
    def __init__(self, extractor: EntityExtractor, graph_store: GraphStore) -> None:
        self.extractor = extractor
        self.graph_store = graph_store

    def search(self, question: str, top_k: int = 4) -> list[Source]:
        query_entities = self.extractor.extract(question, max_entities=12)
        if not query_entities:
            return []
        return self.graph_store.query(query_entities, top_k=top_k)
