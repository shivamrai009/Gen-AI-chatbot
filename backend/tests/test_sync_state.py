from pathlib import Path

from app.services.sync_state import SyncStateStore


def test_sync_state_roundtrip(tmp_path: Path) -> None:
    store = SyncStateStore(str(tmp_path / "manifest.json"))
    records = {
        "https://example.com": store.stamp(url="https://example.com", checksum="abc123"),
    }

    store.save(records)
    loaded = store.load()

    assert "https://example.com" in loaded
    assert loaded["https://example.com"].checksum == "abc123"
