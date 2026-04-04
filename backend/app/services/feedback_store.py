import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class FeedbackItem:
    trace_id: str
    vote: str
    comment: str | None
    created_at: str


class FeedbackStore:
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)

    def append(self, trace_id: str, vote: str, comment: str | None = None) -> None:
        payload = self._load()
        payload.append(
            {
                "trace_id": trace_id,
                "vote": vote,
                "comment": comment,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        return json.loads(self.file_path.read_text(encoding="utf-8"))
