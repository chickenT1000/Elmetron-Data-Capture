import json
from datetime import datetime
from pathlib import Path

from elmetron.storage.database import Database, DeviceMetadata, StorageConfig


def _make_config(tmp_path: Path, retention_days: int = 365) -> StorageConfig:
    return StorageConfig(
        database_path=tmp_path / "retention.sqlite",
        ensure_directories=True,
        retention_days=retention_days,
    )


def test_retention_purge_logs_audit_event(tmp_path: Path) -> None:
    config = _make_config(tmp_path, retention_days=365)
    database = Database(config)
    database.initialise()

    session = database.start_session(
        datetime(2020, 1, 1, 0, 0, 0),
        DeviceMetadata(serial="TEST-001", description="Test meter", model="CX-505"),
    )

    session.set_metadata({"operator": "alice"})

    decoded_frame = {
        "raw_hex": "00",
        "captured_at": "2020-01-01T00:00:00Z",
        "measurement": {
            "timestamp": "2020-01-01T00:00:00Z",
            "value": -61.2,
            "value_unit": "mV",
            "temperature": 26.1,
            "temperature_unit": "deg C",
        },
    }

    stored = session.store_capture(
        captured_at=datetime(2020, 1, 1, 0, 0, 0),
        raw_frame=b"\x00",
        decoded=decoded_frame,
    )

    database.set_derived_metrics(stored.measurement_id, {"stability": 0.5})

    conn = database.connect()
    with conn:
        conn.execute(
            "INSERT INTO annotations (measurement_id, author, body) VALUES (?, ?, ?)",
            (stored.measurement_id, "alice", "baseline"),
        )

    session.log_event("info", "test", "historic entry")
    session.close(datetime(2020, 1, 2, 0, 0, 0))

    database.apply_retention(datetime(2025, 1, 1, 0, 0, 0))

    conn = database.connect()
    remaining_sessions = conn.execute("SELECT id, note FROM sessions").fetchall()

    # original session should be purged, retention log session should remain
    assert all(row[0] != session.id for row in remaining_sessions)
    assert any(row[1] == "Retention log" for row in remaining_sessions)

    retention_events = conn.execute(
        "SELECT session_id, category, payload_json FROM audit_events WHERE category = 'retention'"
    ).fetchall()
    assert retention_events, "expected a retention audit event"

    retention_event = retention_events[0]
    retention_payload = json.loads(retention_event[2])

    # ensure payload tracks removal counts
    changes = retention_payload["changes"]
    assert changes, "retention payload should list affected sessions"
    summary = next(item for item in changes if item["session_id"] == session.id)
    assert summary["removed_measurements"] == 1
    assert summary["removed_derived_metrics"] == 1
    assert summary["removed_annotations"] == 1
    assert summary["removed_metadata"] == 1
    assert summary["removed_audit_events"] == 1
    assert summary["removed_frames"] == 1
    assert summary["session_deleted"] is True

    retention_session_id = retention_event[0]
    retention_session_note = conn.execute(
        "SELECT note FROM sessions WHERE id = ?",
        (retention_session_id,),
    ).fetchone()
    assert retention_session_note is not None
    assert retention_session_note[0] == "Retention log"

    # ensure related tables are cleared
    for table in ["measurements", "raw_frames", "derived_metrics", "annotations", "session_metadata"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count == 0, f"expected {table} to be empty after retention"
