import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.models.schemas import Source


@dataclass
class GraphEvidence:
    entity: str
    source: Source


class GraphStore:
    def __init__(self, graph_path: str) -> None:
        self.graph_path = Path(graph_path)

    def clear(self) -> None:
        self._save({"entities": {}, "edges": {}})

    def upsert_chunk_entities(
        self,
        url: str,
        title: str,
        snippet: str,
        section: str,
        entities: list[str],
    ) -> None:
        if not entities:
            return

        graph = self._load()
        entity_store: dict[str, list[dict[str, str]]] = graph["entities"]
        edge_store: dict[str, int] = graph["edges"]

        unique_entities = sorted({entity.strip() for entity in entities if entity.strip()})
        for entity in unique_entities:
            records = entity_store.setdefault(entity, [])
            record = {"url": url, "title": title, "snippet": snippet[:240], "section": section}
            if record not in records:
                records.append(record)
                if len(records) > 40:
                    del records[0 : len(records) - 40]

        for left_index in range(len(unique_entities)):
            for right_index in range(left_index + 1, len(unique_entities)):
                left = unique_entities[left_index]
                right = unique_entities[right_index]
                key = self._edge_key(left, right)
                edge_store[key] = int(edge_store.get(key, 0)) + 1

        self._save(graph)

    def delete_by_urls(self, urls: list[str]) -> None:
        if not urls:
            return

        graph = self._load()
        url_set = set(urls)
        updated_entities: dict[str, list[dict[str, str]]] = {}
        for entity, records in graph["entities"].items():
            kept = [record for record in records if record.get("url") not in url_set]
            if kept:
                updated_entities[entity] = kept

        graph["entities"] = updated_entities
        graph["edges"] = self._rebuild_edges(updated_entities)
        self._save(graph)

    def query(self, query_entities: list[str], top_k: int = 4) -> list[Source]:
        graph = self._load()
        entity_store: dict[str, list[dict[str, str]]] = graph["entities"]
        edge_store: dict[str, int] = graph["edges"]

        scores: dict[tuple[str, str], float] = defaultdict(float)
        for query_entity in query_entities:
            if query_entity in entity_store:
                self._score_entity_records(scores, query_entity, entity_store, boost=1.0)

            for edge_key, weight in edge_store.items():
                left, right = edge_key.split("||", maxsplit=1)
                if query_entity == left and right in entity_store:
                    self._score_entity_records(scores, right, entity_store, boost=0.25 * weight)
                elif query_entity == right and left in entity_store:
                    self._score_entity_records(scores, left, entity_store, boost=0.25 * weight)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        sources: list[Source] = []
        for (url, snippet), _ in ranked[:top_k]:
            for records in entity_store.values():
                for record in records:
                    if record.get("url") == url and record.get("snippet") == snippet:
                        sources.append(
                            Source(
                                title=record.get("title", "Unknown"),
                                url=url,
                                snippet=snippet,
                                section=record.get("section") or None,
                            )
                        )
                        break
                if len(sources) >= top_k:
                    break
            if len(sources) >= top_k:
                break

        return sources

    def _score_entity_records(
        self,
        scores: dict[tuple[str, str], float],
        entity: str,
        entity_store: dict[str, list[dict[str, str]]],
        boost: float,
    ) -> None:
        for record in entity_store.get(entity, []):
            key = (record.get("url", ""), record.get("snippet", ""))
            scores[key] += boost

    def _edge_key(self, left: str, right: str) -> str:
        ordered = sorted([left, right])
        return f"{ordered[0]}||{ordered[1]}"

    def _rebuild_edges(self, entities: dict[str, list[dict[str, str]]]) -> dict[str, int]:
        by_url: dict[str, set[str]] = defaultdict(set)
        for entity, records in entities.items():
            for record in records:
                by_url[record.get("url", "")].add(entity)

        edges: dict[str, int] = {}
        for entity_set in by_url.values():
            entity_list = sorted(entity_set)
            for left_index in range(len(entity_list)):
                for right_index in range(left_index + 1, len(entity_list)):
                    key = self._edge_key(entity_list[left_index], entity_list[right_index])
                    edges[key] = int(edges.get(key, 0)) + 1
        return edges

    def _load(self) -> dict:
        if not self.graph_path.exists():
            return {"entities": {}, "edges": {}}
        return json.loads(self.graph_path.read_text(encoding="utf-8"))

    def _save(self, graph: dict) -> None:
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.write_text(json.dumps(graph, ensure_ascii=True, indent=2), encoding="utf-8")
