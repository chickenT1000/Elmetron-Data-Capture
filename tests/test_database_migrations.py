from __future__ import annotations

from elmetron.config import StorageConfig
from elmetron.storage.database import Database


def test_database_creates_overlay_indexes(tmp_path):
    db_path = tmp_path / 'indexed.sqlite'
    config = StorageConfig(
        database_path=db_path,
        ensure_directories=True,
        vacuum_on_start=False,
        retention_days=None,
    )

    database = Database(config)
    database.initialise()

    conn = database.connect()
    measurement_indexes = {row['name'] for row in conn.execute("PRAGMA index_list('measurements')")}
    raw_frame_indexes = {row['name'] for row in conn.execute("PRAGMA index_list('raw_frames')")}
    user_version = conn.execute('PRAGMA user_version').fetchone()[0]

    assert 'idx_measurements_session_timestamp' in measurement_indexes
    assert 'idx_raw_frames_session_captured_at' in raw_frame_indexes
    assert user_version >= 1

    database.close()
