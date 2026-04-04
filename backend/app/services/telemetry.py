import json
from datetime import datetime, timezone
from pathlib import Path


class TelemetryService:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def log(self, trace_id: str, stage: str, payload: dict, elapsed_ms: float | None = None) -> None:
        item = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "stage": stage,
            "elapsed_ms": elapsed_ms,
            "payload": payload,
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=True) + "\n")
