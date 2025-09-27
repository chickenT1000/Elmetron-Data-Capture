import datetime

import pytest

from elmetron.api.health import HealthMonitor
from elmetron.config import MonitoringConfig
from elmetron.acquisition.service import ServiceStats


class _DummyService:
    def __init__(self) -> None:
        self.stats = ServiceStats(last_window_started=datetime.datetime.utcnow())
        self._stop_requested = False  # pylint: disable=protected-access

    def command_metrics(self):
        return {
            'queue_depth': 0,
            'result_backlog': 0,
            'inflight': 0,
            'scheduled': [],
            'worker_running': False,
            'async_enabled': False,
        }


def test_snapshot_without_monitoring_returns_no_log_rotation():
    service = _DummyService()
    service.stats.interface_lock.max_wait_s = 1.25
    service.stats.interface_lock.average_hold_s = 0.5
    service.stats.analytics_profile = {'frames_processed': 5, 'average_processing_time_ms': 2.5}
    service.stats.interface_lock.max_wait_s = 1.25
    service.stats.interface_lock.average_hold_s = 0.5
    monitor = HealthMonitor(service)

    snapshot = monitor.snapshot()
    assert snapshot.interface_lock is not None
    assert snapshot.interface_lock['max_wait_s'] == pytest.approx(1.25)
    assert snapshot.interface_lock['average_hold_s'] == pytest.approx(0.5)
    assert snapshot.analytics_profile is not None
    assert snapshot.analytics_profile['frames_processed'] == 5
    assert snapshot.response_times is not None
    assert snapshot.response_times['samples'] >= 1
    assert snapshot.interface_lock['max_wait_s'] == pytest.approx(1.25)
    assert snapshot.interface_lock['average_hold_s'] == pytest.approx(0.5)


def test_log_rotation_status_cached(monkeypatch):
    service = _DummyService()
    config = MonitoringConfig(
        log_rotation_task='ElmetronLogRotate',
        log_rotation_max_age_minutes=180,
        log_rotation_probe_interval_s=300,
    )
    monitor = HealthMonitor(service, config)

    calls = []

    def _fake_check(task_name: str, max_age: int):  # pylint: disable=unused-argument
        calls.append((task_name, max_age))
        return {'status': 'ok', 'name': task_name}

    monkeypatch.setattr('elmetron.api.health._check_log_rotation_task', _fake_check)

    first = monitor.snapshot()
    assert first.log_rotation == {'status': 'ok', 'name': 'ElmetronLogRotate'}
    assert len(calls) == 1

    second = monitor.snapshot()
    assert second.log_rotation == {'status': 'ok', 'name': 'ElmetronLogRotate'}
    assert len(calls) == 1  # cached within interval

    monitor._log_rotation_checked_at = datetime.datetime.utcnow() - datetime.timedelta(  # type: ignore[attr-defined]
        seconds=config.log_rotation_probe_interval_s + 5
    )

    third = monitor.snapshot()
    assert third.log_rotation == {'status': 'ok', 'name': 'ElmetronLogRotate'}
    assert len(calls) == 2




def test_recent_events_returns_empty_without_database():
    service = _DummyService()
    monitor = HealthMonitor(service)

    assert monitor.recent_events() == []


def test_recent_events_delegates_to_database():
    service = _DummyService()

    class _FakeDatabase:
        def __init__(self) -> None:
            self.calls = []

        def recent_audit_events(self, **kwargs):
            self.calls.append(kwargs)
            return [{'id': 1, 'message': 'ok'}]

    fake_db = _FakeDatabase()
    service.database = fake_db  # type: ignore[attr-defined]
    monitor = HealthMonitor(service)

    events = monitor.recent_events(limit=5, since_id=10)

    assert events == [{'id': 1, 'message': 'ok'}]
    assert fake_db.calls == [{'limit': 5, 'since_id': 10}]



def test_record_watchdog_event_tracks_history():
    service = _DummyService()
    monitor = HealthMonitor(service)

    now = datetime.datetime.utcnow()
    monitor.record_watchdog_event('timeout', 'No frames observed', now, {'frames': 0})
    monitor.record_watchdog_event('recovery', 'Frames recovered', now + datetime.timedelta(seconds=5))

    snapshot = monitor.snapshot()

    assert snapshot.watchdog_alert is None
    assert snapshot.watchdog_history is not None
    assert [event['kind'] for event in snapshot.watchdog_history][:2] == ['recovery', 'timeout']




