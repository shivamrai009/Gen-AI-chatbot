from pathlib import Path

from app.services.feedback_store import FeedbackStore


def test_feedback_store_appends_items(tmp_path: Path) -> None:
    store = FeedbackStore(str(tmp_path / "feedback.json"))
    store.append(trace_id="trace-1", vote="up", comment="good")
    store.append(trace_id="trace-2", vote="down", comment=None)

    payload = (tmp_path / "feedback.json").read_text(encoding="utf-8")
    assert "trace-1" in payload
    assert "trace-2" in payload
