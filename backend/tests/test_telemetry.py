from pathlib import Path

from app.services.telemetry import TelemetryService


def test_telemetry_writes_log_line(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.log"
    telemetry = TelemetryService(str(path))
    telemetry.log("trace-1", "stage", {"ok": True}, elapsed_ms=4.5)

    text = path.read_text(encoding="utf-8")
    assert "trace-1" in text
    assert '"stage"' in text
