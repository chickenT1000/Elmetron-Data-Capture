from __future__ import annotations

import io
import json
import zipfile
import http.client
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from urllib import request

from elmetron.acquisition.service import ServiceStats
from elmetron.config import AppConfig, StorageConfig
from elmetron.api.health import HealthMonitor
from elmetron.api.server import HealthApiServer
from elmetron.service.watchdog import CaptureWatchdog
from elmetron.storage.database import Database, DeviceMetadata


def _make_service(**overrides):
    stats = ServiceStats(
        frames=overrides.get('frames', 0),
        bytes_read=overrides.get('bytes_read', 0),
        last_window_bytes=overrides.get('last_window_bytes', 0),
        last_window_started=overrides.get('last_window_started', datetime.utcnow()),
        last_frame_at=overrides.get('last_frame_at'),
    )
    service = SimpleNamespace(stats=stats, _stop_requested=False)
    return service


def _build_database(tmp_path) -> tuple[Database, int]:
    storage = StorageConfig(
        database_path=tmp_path / 'health_api.sqlite',
        ensure_directories=True,
        vacuum_on_start=False,
        retention_days=None,
    )
    database = Database(storage)
    database.initialise()
    started_at = datetime(2025, 9, 27, 10, 0, 0)
    handle = database.start_session(started_at, DeviceMetadata(serial='ABC123', description='CX-505', model='CX-505'))
    for index in range(2):
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
        handle.store_capture(captured, raw_frame=bytes([index]), decoded=payload, derived_metrics={'moving_average': 7.0 + index})
    handle.close(started_at + timedelta(minutes=5))
    return database, handle.id


def _wait_for(predicate, timeout=1.0, interval=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_capture_watchdog_emits_timeout_and_recovery():
    service = _make_service(last_window_started=datetime.utcnow() - timedelta(seconds=1))
    events = []

    watchdog = CaptureWatchdog(
        service,
        timeout_s=0.2,
        poll_interval_s=0.05,
        on_event=events.append,
    )

    watchdog.start()

    assert _wait_for(lambda: events, timeout=1.5)
    assert events[0].kind == 'timeout'

    service.stats.frames = 5
    service.stats.bytes_read = 128
    service.stats.last_frame_at = datetime.utcnow()

    assert _wait_for(lambda: len(events) >= 2, timeout=1.5)
    recovery = events[1]
    assert recovery.kind == 'recovery'
    assert recovery.payload and recovery.payload['frames'] == 5

    watchdog.stop()
    event_count = len(events)
    time.sleep(0.1)
    assert len(events) == event_count


def test_capture_watchdog_stop_is_idempotent():
    service = _make_service()
    watchdog = CaptureWatchdog(service, timeout_s=0.5, poll_interval_s=0.05)
    watchdog.start()
    watchdog.stop()
    watchdog.stop()


def test_health_api_server_serves_snapshot_and_shuts_down():
    service = _make_service()
    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)

    server.start()
    host, port = server.address
    url = f"http://{host}:{port}/health"

    def fetch():
        with request.urlopen(url, timeout=1) as response:
            assert response.status == 200
            return json.loads(response.read().decode('utf-8'))

    payload = fetch()
    assert payload['state'] == 'running'
    assert payload['frames'] == 0

    service.stats.frames = 3
    service.stats.last_frame_at = datetime.utcnow()

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda _: fetch(), range(5)))

    assert all(result['frames'] == 3 for result in results)

    server.stop()
    thread = getattr(server, '_thread', None)
    if thread is not None:
        assert not thread.is_alive()

    server.stop()


def test_health_api_logs_endpoint_returns_events():
    events = [
        {'id': 1, 'session_id': 10, 'level': 'info', 'category': 'session', 'message': 'Started', 'payload': None, 'created_at': '2025-09-26T10:00:00Z'},
        {'id': 2, 'session_id': 10, 'level': 'warning', 'category': 'capture', 'message': 'Window hiccup', 'payload': {'bytes': 0}, 'created_at': '2025-09-26T10:05:00Z'},
    ]

    class FakeDatabase:
        def __init__(self) -> None:
            self.calls = []

        def recent_audit_events(self, **kwargs):
            self.calls.append(kwargs)
            return events

    service = _make_service()
    service.database = FakeDatabase()

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        url = f"http://{host}:{port}/health/logs?limit=5"
        with request.urlopen(url, timeout=1) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode('utf-8'))
        assert payload['events'] == events
        assert service.database.calls == [{'limit': 5, 'since_id': None}]
    finally:
        server.stop()



def test_health_api_logs_ndjson_returns_events():
    events = [
        {'id': 1, 'message': 'one'},
        {'id': 2, 'message': 'two'},
    ]

    class FakeDatabase:
        def __init__(self) -> None:
            self.calls = []

        def recent_audit_events(self, **kwargs):
            self.calls.append(kwargs)
            return events

    service = _make_service()
    service.database = FakeDatabase()

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        url = f"http://{host}:{port}/health/logs.ndjson?limit=2"
        with request.urlopen(url, timeout=1) as response:
            assert response.status == 200
            body = response.read().decode('utf-8').splitlines()
        assert len(body) == 2
        decoded = [json.loads(line) for line in body]
        assert decoded == events
        assert service.database.calls == [{'limit': 2, 'since_id': None}]
    finally:
        server.stop()


def test_health_api_logs_ndjson_filters_level_and_category():
    events = [
        {'id': 1, 'level': 'info', 'category': 'session'},
        {'id': 2, 'level': 'warning', 'category': 'capture'},
    ]

    class FakeDatabase:
        def recent_audit_events(self, **kwargs):
            return events

    service = _make_service()
    service.database = FakeDatabase()

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        url = f"http://{host}:{port}/health/logs.ndjson?limit=5&level=warning&category=capture"
        with request.urlopen(url, timeout=1) as response:
            assert response.status == 200
            body = response.read().decode('utf-8').splitlines()
        assert len(body) == 1
        assert json.loads(body[0])['id'] == 2
    finally:
        server.stop()


def test_health_api_sessions_recent_endpoint(tmp_path):
    database, session_id = _build_database(tmp_path)
    service = _make_service()
    service.database = database

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        url = f"http://{host}:{port}/sessions/recent?limit=5"
        with request.urlopen(url, timeout=1) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode('utf-8'))
        assert payload['sessions']
        assert payload['sessions'][0]['id'] == session_id
    finally:
        server.stop()
        database.close()


def test_health_api_session_evaluation_endpoint(tmp_path):
    database, session_id = _build_database(tmp_path)
    service = _make_service()
    service.database = database

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        url = f"http://{host}:{port}/sessions/{session_id}/evaluation?anchor=calibration"
        with request.urlopen(url, timeout=1) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode('utf-8'))
        assert payload['session']['session_id'] == session_id
        assert payload['series']
        assert payload['samples'] == len(payload['series'])
    finally:
        server.stop()
        database.close()


def test_health_api_session_evaluation_export(tmp_path):
    database, session_id = _build_database(tmp_path)
    service = _make_service()
    service.database = database

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        path = f"/sessions/{session_id}/evaluation/export?format=json&filename=evaluation.json"
        conn = http.client.HTTPConnection(host, port)
        conn.request('GET', path)
        response = conn.getresponse()
        assert response.status == 200
        disposition = response.getheader('Content-Disposition')
        assert disposition and 'evaluation.json' in disposition
        body = response.read()
        payload = json.loads(body.decode('utf-8'))
        assert payload['session']['session_id'] == session_id
    finally:
        server.stop()
        database.close()







def test_health_api_log_stream_emits_events_in_order():
    events = [
        {
            'id': 1,
            'session_id': 42,
            'level': 'info',
            'category': 'session',
            'message': 'Session started',
            'payload': None,
            'created_at': '2025-09-26T11:00:00Z',
        },
        {
            'id': 2,
            'session_id': 42,
            'level': 'warning',
            'category': 'capture',
            'message': 'Transient glitch',
            'payload': {'bytes': 0},
            'created_at': '2025-09-26T11:00:05Z',
        },
    ]

    class StreamDatabase:
        def __init__(self) -> None:
            self.calls = []

        def recent_audit_events(self, **kwargs):
            self.calls.append(kwargs)
            since_id = kwargs.get('since_id')
            if since_id is None:
                return list(events)
            try:
                threshold = int(since_id)
            except (TypeError, ValueError):
                threshold = None
            if threshold is None:
                return list(events)
            return [item for item in events if item['id'] > threshold]

    service = _make_service()
    service.database = StreamDatabase()

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request('GET', '/health/logs/stream?limit=5')
        response = conn.getresponse()
        assert response.status == 200

        payloads = []
        stream = response.fp
        for _ in range(12):
            line = stream.readline()
            if not line:
                break
            decoded = line.decode('utf-8').strip()
            if not decoded:
                continue
            if decoded.startswith('data: '):
                payload = json.loads(decoded[6:])
                payloads.append(payload)
                if len(payloads) >= 2:
                    break
        conn.close()
    finally:
        server.stop()

    assert [item['id'] for item in payloads] == [1, 2]
    assert any(call.get('since_id') is None for call in service.database.calls)


def test_health_api_log_stream_emits_heartbeat(monkeypatch):
    events = []

    class EmptyDatabase:
        def __init__(self) -> None:
            self.calls = []

        def recent_audit_events(self, **kwargs):
            self.calls.append(kwargs)
            return []

    service = _make_service()
    service.database = EmptyDatabase()

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request('GET', '/health/logs/stream?limit=5&interval_s=0.05&heartbeat_s=0.1')
        response = conn.getresponse()
        assert response.status == 200

        lines = []
        stream = response.fp
        start = time.time()
        while time.time() - start < 0.5 and len(lines) < 4:
            line = stream.readline()
            if not line:
                break
            decoded = line.decode('utf-8').strip()
            if decoded:
                lines.append(decoded)
        conn.close()
    finally:
        server.stop()

    assert any(line.startswith(': heartbeat') for line in lines)
    assert service.database.calls  # ensure recent events queried at least once


def test_health_api_bundle_returns_zip(tmp_path):
    class BundleDatabase:
        def __init__(self, root):
            self.path = root / 'elmetron.sqlite'
        def recent_audit_events(self, **kwargs):
            return []
        def recent_sessions(self, limit=5):
            return [
                {
                    'id': 42,
                    'started_at': '2025-09-26T09:00:00Z',
                    'ended_at': '2025-09-26T09:15:00Z',
                    'note': 'diagnostic-check',
                    'instrument': {
                        'serial': 'CX505-001',
                        'description': 'CX-505',
                        'model': 'CX-505',
                    },
                    'counts': {
                        'measurements': 12,
                        'frames': 12,
                        'audit_events': 3,
                    },
                    'metadata': {'mode': 'pH'},
                    'latest_measurement_at': '2025-09-26T09:14:30Z',
                }
            ]

    service = _make_service(last_window_started=datetime.utcnow(), last_frame_at=datetime.utcnow())
    service.database = BundleDatabase(tmp_path)
    service._config = AppConfig()
    service._command_definitions = {}

    monitor = HealthMonitor(service)
    server = HealthApiServer(monitor, host='127.0.0.1', port=0)
    server.start()
    try:
        host, port = server.address
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request('GET', '/health/bundle?events=10&sessions=1&filename=test-bundle.zip')
        response = conn.getresponse()
        assert response.status == 200
        assert response.getheader('Content-Disposition') == 'attachment; filename="test-bundle.zip"'
        payload = response.read()
    finally:
        conn.close()
        server.stop()

    archive = zipfile.ZipFile(io.BytesIO(payload))
    names = set(archive.namelist())
    assert 'manifest.json' in names
    assert 'health/snapshot.json' in names
    assert 'storage/recent_sessions.json' in names

    manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
    assert manifest['counts']['events'] == 0  # database returns no audit events
    sessions_payload = json.loads(archive.read('storage/recent_sessions.json').decode('utf-8'))
    assert sessions_payload['sessions'][0]['id'] == 42

