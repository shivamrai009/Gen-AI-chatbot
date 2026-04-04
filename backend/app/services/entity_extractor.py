import re

DOMAIN_TERMS = {
    "gitlab",
    "handbook",
    "direction",
    "okr",
    "engineering",
    "marketing",
    "security",
    "deploy",
    "deployment",
    "ci",
    "cd",
    "pipeline",
    "release",
    "product",
    "strategy",
}


class EntityExtractor:
    def extract(self, text: str, max_entities: int = 20) -> list[str]:
        terms = set()

        for match in re.findall(r"\b[A-Z][A-Za-z0-9\-/]{2,}\b", text):
            terms.add(match.strip())

        for match in re.findall(r"\b[a-z][a-z0-9\-/]{2,}\b", text.lower()):
            if match in DOMAIN_TERMS:
                terms.add(match)

        ranked = sorted(terms, key=lambda item: (-len(item), item.lower()))
        return ranked[:max_entities]
