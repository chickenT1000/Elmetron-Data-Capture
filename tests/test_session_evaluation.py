from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from elmetron.config import StorageConfig
from elmetron.reporting.session import build_session_evaluation
from elmetron.storage.database import Database, DeviceMetadata


def _seed_session(database: Database) -> int:
    started_at = datetime(2025, 9, 27, 10, 0, 0)
    handle = database.start_session(started_at, DeviceMetadata(serial='ABC123', description='CX-505', model='CX-505'))
    for index in range(3):
        captured = started_at + timedelta(minutes=index)
        payload = {
            'measurement': {
                'timestamp': captured.isoformat(),
                'value': 7.0 + index,
                'value_unit': 'pH',
                'temperature': 20.0 + index,
                'temperature_unit': 'C',
                'mode': 'calibration' if index == 1 else 'measurement',
            },
        }
        derived = {'moving_average': 7.0 + index}
        handle.store_capture(captured, raw_frame=bytes([index]), decoded=payload, derived_metrics=derived)
    handle.close(started_at + timedelta(minutes=4))
    return handle.id


def _database(tmp_path) -> Database:
    storage = StorageConfig(
        database_path=tmp_path / 'elmetron.sqlite',
        ensure_directories=True,
        vacuum_on_start=False,
        retention_days=None,
    )
    database = Database(storage)
    database.initialise()
    return database


def test_build_session_evaluation_uses_calibration_anchor(tmp_path):
    database = _database(tmp_path)
    session_id = _seed_session(database)

    evaluation = build_session_evaluation(database, session_id, anchor='calibration')
    assert evaluation is not None
    assert evaluation['samples'] == 3
    assert evaluation['anchor'] == 'calibration'
    offsets = [entry['offset_seconds'] for entry in evaluation['series']]
    assert offsets[1] == pytest.approx(0.0, abs=1e-6)
    assert offsets[0] is not None and offsets[0] < 0
    assert offsets[2] is not None and offsets[2] > 0
    assert evaluation['statistics']['value']['average'] == pytest.approx(8.0)
    assert evaluation['statistics']['value']['unit'] == 'pH'
    assert evaluation['statistics']['temperature']['unit'] == 'C'
    assert evaluation['duration_seconds'] == pytest.approx(120.0)
    assert len(evaluation['markers']) == 1


def test_build_session_evaluation_falls_back_to_start_anchor(tmp_path):
    database = _database(tmp_path)
    session_id = _seed_session(database)

    evaluation = build_session_evaluation(database, session_id, anchor='start')
    assert evaluation is not None
    assert evaluation['anchor'] == 'start'
    assert evaluation['series'][0]['offset_seconds'] == pytest.approx(0.0, abs=1e-6)
