from __future__ import annotations

from datetime import datetime, timedelta

from elmetron.config import StorageConfig
from elmetron.storage.database import Database, DeviceMetadata


def _create_database(tmp_path):
    storage = StorageConfig(database_path=tmp_path / 'events.sqlite', ensure_directories=False)
    database = Database(storage)
    database.initialise()
    return database


def test_recent_audit_events_returns_latest_first(tmp_path):
    database = _create_database(tmp_path)
    handle = database.start_session(
        datetime.utcnow(),
        DeviceMetadata(serial='123', description='Demo', model='CX-505'),
    )

    handle.log_event('info', 'session', 'Session started')
    handle.log_event('warning', 'capture', 'Capture hiccup', {'code': 42})
    handle.log_event('debug', 'capture', 'Window stats', {'bytes': 128})

    events = database.recent_audit_events(limit=2)

    assert len(events) == 2
    assert events[0]['message'] == 'Window stats'
    assert events[0]['payload'] == {'bytes': 128}
    assert events[1]['message'] == 'Capture hiccup'
    assert events[1]['payload'] == {'code': 42}


def test_recent_audit_events_supports_since_id(tmp_path):
    database = _create_database(tmp_path)
    handle = database.start_session(
        datetime.utcnow() - timedelta(minutes=1),
        DeviceMetadata(serial='ABC', description=None, model='CX-505'),
    )

    handle.log_event('info', 'session', 'Event 1')
    handle.log_event('info', 'session', 'Event 2')
    handle.log_event('info', 'session', 'Event 3')

    all_events = database.recent_audit_events(limit=5)
    assert len(all_events) == 3

    newest_id = all_events[0]['id']
    middle_id = all_events[1]['id']

    filtered = database.recent_audit_events(limit=5, since_id=middle_id)
    assert filtered
    assert all(event['id'] > middle_id for event in filtered)
    assert filtered[0]['id'] == newest_id
