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

    database.append_system_audit_event(__import__('elmetron.storage.database', fromlist=['AuditEvent']).AuditEvent('info', 'system', 'old log', {}))
    with conn:
        conn.execute("UPDATE audit_events SET created_at='2020-01-01' WHERE session_id IS NULL")
    database.apply_retention(datetime(2025, 1, 1))
    for table in ('sessions','measurements','raw_frames','derived_metrics','annotations','session_metadata'):
        assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE session_id=?", (session.id,)).fetchone()[0] == 1
    events = conn.execute("SELECT payload_json FROM audit_events WHERE category='retention'").fetchall()
    assert len(events) == 1
    assert json.loads(events[0][0])['deleted_system_logs'] == 1
    database.close()
