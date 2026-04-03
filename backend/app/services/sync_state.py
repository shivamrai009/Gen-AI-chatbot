import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SyncRecord:
    url: str
    checksum: str
    synced_at: str


class SyncStateStore:
    def __init__(self, manifest_path: str) -> None:
        self.manifest_path = Path(manifest_path)

    def load(self) -> dict[str, SyncRecord]:
        if not self.manifest_path.exists():
            return {}

        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {
            item["url"]: SyncRecord(
                url=item["url"],
                checksum=item["checksum"],
                synced_at=item["synced_at"],
            )
            for item in payload
        }

    def save(self, records: dict[str, SyncRecord]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(records.values(), key=lambda item: item.url)
        payload = [
            {"url": item.url, "checksum": item.checksum, "synced_at": item.synced_at}
            for item in ordered
        ]
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def stamp(self, url: str, checksum: str) -> SyncRecord:
        return SyncRecord(url=url, checksum=checksum, synced_at=datetime.now(timezone.utc).isoformat())
