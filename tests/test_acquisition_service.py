from __future__ import annotations

import types
from typing import List

import time

import pytest

from elmetron.acquisition.service import AcquisitionService, InterfaceLockStats, _InterfaceLockMonitor
from elmetron.commands.executor import CommandDefinition, CommandResult
from elmetron.config import AppConfig, ScheduledCommandConfig
from elmetron.hardware import ListedDevice


class DummyInterface:
    """Minimal stub exposing the acquisition interface API."""

    def __init__(self) -> None:
        self.writes: List[List[bytes]] = []

    def write(self, payloads):  # pragma: no cover - unused in this test
        self.writes.append(list(payloads))
        return sum(len(p) for p in payloads)


class DummySession:
    def __init__(self) -> None:
        self.events = []
        self.id = 123

    def log_event(self, level, category, message, payload=None) -> None:  # noqa: D401 - simple stub
        self.events.append((level, category, message, payload))


class DummyIngestor:
    def __init__(self) -> None:
        self.frames = 0
        self.seen = []

    def handle_frame(self, frame):
        self.frames += 1
        self.seen.append(frame)
        return {'frame_hex': frame.hex()}


class _FakeRegistry:
    def __init__(self) -> None:
        self.profiles = {
            'cx505': {
                'name': 'cx505',
                'commands': {
                    'run_ok': CommandDefinition(name='run_ok', read_duration_s=0.1),
                },
            },
            'cx505_safe': {
                'name': 'cx505_safe',
                'commands': {
                    'safe_ping': CommandDefinition(name='safe_ping', read_duration_s=0.1),
                },
            },
        }

    def apply_to_device(self, device_config):
        requested = (device_config.profile or '').strip().lower()
        profile = self.profiles.get(requested)
        if profile is None:
            raise KeyError(f'profile {requested} not found')
        device_config.profile = profile['name']
        return types.SimpleNamespace(name=profile['name'], commands=profile['commands'])


@pytest.fixture()
def base_service() -> AcquisitionService:
    config = AppConfig()
    config.acquisition.startup_commands = ['run_ok', 'missing', 'run_fail']
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_max_retries = 1
    config.acquisition.default_command_retry_backoff_s = 0.0

    command_definitions = {
        'run_ok': CommandDefinition(name='run_ok', read_duration_s=0.1),
        'run_fail': CommandDefinition(name='run_fail', read_duration_s=0.1),
    }

    results = {
        'run_ok': CommandResult(
            name='run_ok',
            written_bytes=4,
            frames=[b'\x01\x02'],
            bytes_read=2,
            duration_s=0.05,
            expected_hex=None,
            matched_expectation=None,
        )
    }

    def runner(interface, definition):
        if definition.name == 'run_fail':
            raise RuntimeError('boom')
        return results[definition.name]

    return AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )


def test_startup_commands_run_and_log(base_service: AcquisitionService) -> None:
    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    base_service._run_startup_commands(interface, session, ingestor)  # pylint: disable=protected-access

    # Expect bytes recorded and frames ingested for successful command.
    assert base_service.stats.bytes_read == 2
    assert ingestor.frames == 1
    assert ingestor.seen == [b'\x01\x02']

    # Verify session log events for missing and failing commands.
    levels = [entry[0] for entry in session.events]
    messages = [entry[2] for entry in session.events]
    pairs = list(zip(levels, messages))
    assert ('info', 'Startup command executed') in pairs
    assert any(msg == 'Startup command not defined' for msg in messages)
    assert any(msg == 'Startup command failed' for msg in messages)

    success_payload = next(payload for (_, _, msg, payload) in session.events if msg == 'Startup command executed')
    assert success_payload['retry_policy'] == {'max_retries': 1, 'backoff_s': 0.0}
    assert success_payload['lab_retry_applied'] is False

    failure_payload = next(payload for (_, _, msg, payload) in session.events if msg == 'Startup command failed')
    assert failure_payload['error_type'] == 'RuntimeError'
    assert failure_payload['retry_policy'] == {'max_retries': 1, 'backoff_s': 0.0}
    assert failure_payload['lab_retry_applied'] is False

def test_scheduled_command_runs_on_startup_with_retry() -> None:
    config = AppConfig()
    config.acquisition.startup_commands = []
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_retry_backoff_s = 0.0
    config.acquisition.scheduled_commands = [
        ScheduledCommandConfig(
            name='run_retry',
            run_on_startup=True,
            interval_s=10.0,
            max_retries=1,
            retry_backoff_s=0.0,
        )
    ]

    command_definitions = {
        'run_retry': CommandDefinition(name='run_retry', read_duration_s=0.1),
    }

    attempts = {'count': 0}

    def runner(interface, definition):
        attempts['count'] += 1
        if attempts['count'] == 1:
            raise RuntimeError('transient failure')
        return CommandResult(
            name='run_retry',
            written_bytes=3,
            frames=[b'\x10\x20'],
            bytes_read=2,
            duration_s=0.02,
            expected_hex=None,
            matched_expectation=True,
        )

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )

    assert service._scheduled_states  # pylint: disable=protected-access
    state = service._scheduled_states[0]  # pylint: disable=protected-access

    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    service._reset_schedule(time.time())  # pylint: disable=protected-access
    service._run_startup_commands(interface, session, ingestor)  # pylint: disable=protected-access

    assert attempts['count'] == 2
    assert state.runs == 1
    assert state.next_due is not None

    startup_events = [payload for (_, _, msg, payload) in session.events if msg == 'Startup command executed']
    assert startup_events
    assert startup_events[0]['source'] == 'startup'
    assert 'schedule' in startup_events[0]
    assert startup_events[0]['retry_policy']['max_retries'] == 1
    assert startup_events[0]['lab_retry_applied'] is False


def test_process_scheduled_command_runs_when_due() -> None:
    config = AppConfig()
    config.acquisition.startup_commands = []
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.scheduled_commands = [
        ScheduledCommandConfig(
            name='run_ok',
            interval_s=5.0,
        )
    ]

    command_definitions = {
        'run_ok': CommandDefinition(name='run_ok', read_duration_s=0.0),
    }

    result = CommandResult(
        name='run_ok',
        written_bytes=0,
        frames=[],
        bytes_read=0,
        duration_s=0.01,
        expected_hex=None,
        matched_expectation=None,
    )

    def runner(interface, definition):
        return result

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )

    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    service._reset_schedule(0.0)  # pylint: disable=protected-access
    state = service._scheduled_states[0]  # pylint: disable=protected-access

    assert state.next_due == 0.0

    service._process_scheduled_commands(interface, session, ingestor, now=0.0)  # pylint: disable=protected-access

    assert state.runs == 1
    assert state.next_due == pytest.approx(5.0)
    assert any(msg == 'Scheduled command executed' for _, _, msg, _ in session.events)


def test_async_scheduled_command_executes_in_background() -> None:
    config = AppConfig()
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_retry_backoff_s = 0.0
    config.acquisition.scheduled_commands = [
        ScheduledCommandConfig(
            name='async_cmd',
            interval_s=5.0,
            enabled=True,
        )
    ]

    command_definitions = {
        'async_cmd': CommandDefinition(name='async_cmd', read_duration_s=0.0),
    }

    result = CommandResult(
        name='async_cmd',
        written_bytes=0,
        frames=[],
        bytes_read=0,
        duration_s=0.01,
        expected_hex=None,
        matched_expectation=None,
    )

    calls: List[str] = []

    def runner(interface, definition):
        calls.append(definition.name)
        return result

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=True,
    )

    interface = DummyInterface()
    service._start_command_worker(interface)  # pylint: disable=protected-access
    try:
        service._reset_schedule(0.0)  # pylint: disable=protected-access
        state = service._scheduled_states[0]  # pylint: disable=protected-access

        session = DummySession()
        ingestor = DummyIngestor()

        service._process_scheduled_commands(interface, session, ingestor, now=0.0)  # pylint: disable=protected-access
        service._command_queue.join()  # pylint: disable=protected-access
        service._drain_command_results(session, ingestor)  # pylint: disable=protected-access

        assert calls == ['async_cmd']
        assert state.runs == 1
        assert not state.in_flight
        assert any(msg == 'Scheduled command executed' for _, _, msg, _ in session.events)
    finally:
        service._shutdown_command_worker()  # pylint: disable=protected-access


def test_scheduled_command_failure_logs_error_type() -> None:
    config = AppConfig()
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_max_retries = 1
    config.acquisition.default_command_retry_backoff_s = 0.0
    config.acquisition.scheduled_commands = [
        ScheduledCommandConfig(
            name='fail_cmd',
            interval_s=5.0,
            enabled=True,
        )
    ]

    command_definitions = {
        'fail_cmd': CommandDefinition(name='fail_cmd', read_duration_s=0.1),
    }

    def runner(interface, definition):
        raise RuntimeError('boom failure')

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )

    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    service._reset_schedule(0.0)  # pylint: disable=protected-access
    state = service._scheduled_states[0]  # pylint: disable=protected-access

    service._process_scheduled_commands(interface, session, ingestor, now=0.0)  # pylint: disable=protected-access

    failure_payload = next(payload for (_, _, msg, payload) in session.events if msg == 'Scheduled command failed')
    assert failure_payload['error_type'] == 'RuntimeError'
    assert failure_payload['retry_policy'] == {'max_retries': 1, 'backoff_s': 0.0}
    assert failure_payload['lab_retry_applied'] is False
    assert state.runs == 1


def test_scheduled_command_uses_default_retry_policy() -> None:
    config = AppConfig()
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_max_retries = 2
    config.acquisition.default_command_retry_backoff_s = 0.0
    config.acquisition.scheduled_commands = [
        ScheduledCommandConfig(
            name='flaky_cmd',
            interval_s=5.0,
            enabled=True,
        )
    ]

    command_definitions = {
        'flaky_cmd': CommandDefinition(name='flaky_cmd', read_duration_s=0.1),
    }

    attempts = {'count': 0}

    def runner(interface, definition):
        attempts['count'] += 1
        if attempts['count'] < 2:
            raise RuntimeError('transient')
        return CommandResult(
            name='flaky_cmd',
            written_bytes=0,
            frames=[],
            bytes_read=0,
            duration_s=0.01,
            expected_hex=None,
            matched_expectation=None,
        )

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )

    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    service._reset_schedule(0.0)  # pylint: disable=protected-access
    service._process_scheduled_commands(interface, session, ingestor, now=0.0)  # pylint: disable=protected-access

    assert attempts['count'] == 2
    success_payload = next(payload for (_, _, msg, payload) in session.events if msg == 'Scheduled command executed')
    assert success_payload['retry_policy']['max_retries'] == 2
    assert success_payload['lab_retry_applied'] is False


def test_startup_command_lab_retry_applies() -> None:
    config = AppConfig()
    config.acquisition.startup_commands = ['lab_cal']
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_max_retries = 0
    config.acquisition.lab_retry_enabled = True
    config.acquisition.lab_retry_max_retries = 2
    config.acquisition.lab_retry_backoff_s = 0.0
    config.acquisition.lab_retry_categories = ('calibration',)

    command_definitions = {
        'lab_cal': CommandDefinition(
            name='lab_cal',
            read_duration_s=0.1,
            category='calibration',
            calibration_label='ph7_buffer',
            default_max_retries=0,
        )
    }

    attempts = {'count': 0}

    def runner(interface, definition):
        attempts['count'] += 1
        if attempts['count'] < 2:
            raise RuntimeError('transient lab failure')
        return CommandResult(
            name=definition.name,
            written_bytes=4,
            frames=[b'\x01\x02'],
            bytes_read=2,
            duration_s=0.05,
        )

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )

    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    service._run_startup_commands(interface, session, ingestor)  # pylint: disable=protected-access

    assert attempts['count'] == 2
    payload = next(payload for (_, _, msg, payload) in session.events if msg == 'Startup command executed')
    assert payload['lab_retry_applied'] is True
    assert payload['retry_policy']['max_retries'] == 2


def test_scheduled_command_lab_retry_failure_payload() -> None:
    config = AppConfig()
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
    config.acquisition.default_command_max_retries = 0
    config.acquisition.lab_retry_enabled = True
    config.acquisition.lab_retry_max_retries = 3
    config.acquisition.lab_retry_backoff_s = 0.0
    config.acquisition.lab_retry_categories = ('calibration',)
    config.acquisition.scheduled_commands = [
        ScheduledCommandConfig(
            name='lab_sched',
            interval_s=5.0,
            enabled=True,
        )
    ]

    command_definitions = {
        'lab_sched': CommandDefinition(name='lab_sched', read_duration_s=0.1, category='calibration')
    }

    def runner(interface, definition):
        raise RuntimeError('persistent calibration failure')

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions=command_definitions,
        command_runner=runner,
        use_async_commands=False,
    )

    interface = DummyInterface()
    session = DummySession()
    ingestor = DummyIngestor()

    service._reset_schedule(0.0)  # pylint: disable=protected-access
    service._process_scheduled_commands(interface, session, ingestor, now=0.0)  # pylint: disable=protected-access

    failure_payload = next(payload for (_, _, msg, payload) in session.events if msg == 'Scheduled command failed')
    assert failure_payload['lab_retry_applied'] is True
    assert failure_payload['retry_policy']['max_retries'] == 3
    assert failure_payload['attempts'] == 4  # initial attempt + 3 retries


def test_command_metrics_history_tracks_samples() -> None:
    config = AppConfig()
    config.acquisition.quiet = True
    config.device.profile = 'cx505'

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions={},
        use_async_commands=True,
    )

    metrics_first = service.command_metrics()
    metrics_second = service.command_metrics()

    history = metrics_second.get('history')
    assert history is not None
    assert isinstance(history, list)
    assert len(history) >= 2
    entry = history[-1]
    assert 'timestamp_iso' in entry
    assert 'queue_depth' in entry


def test_profile_fallback_triggers_after_decode_failures() -> None:
    config = AppConfig()
    config.device.profile = 'cx505'
    config.device.fallback_profiles = ('cx505_safe',)
    config.acquisition.quiet = True
    config.acquisition.decode_failure_threshold = 2

    registry = _FakeRegistry()

    service = AcquisitionService(
        config,
        database=object(),
        interface_factory=None,
        command_definitions={'run_ok': CommandDefinition(name='run_ok', read_duration_s=0.1)},
        protocol_registry=registry,
        use_async_commands=False,
    )

    session = DummySession()

    service._handle_decode_failure(b'bad', RuntimeError('boom'), session)  # pylint: disable=protected-access
    assert service._profile_switch_pending is None

    service._handle_decode_failure(b'bad', RuntimeError('boom'), session)  # pylint: disable=protected-access

    assert service._profile_switch_pending == 'cx505_safe'
    assert service._current_profile_index == 1  # pylint: disable=protected-access
    assert 'safe_ping' in service._command_definitions
    events = [message for (_, _, message, _) in session.events]
    assert 'Activating fallback profile' in events


def test_interface_lock_monitor_records_wait_and_hold(monkeypatch) -> None:
    stats = InterfaceLockStats()
    monitor = _InterfaceLockMonitor(stats)

    timeline = iter([0.0, 0.1, 0.45, 0.5, 0.8])

    def _fake_perf_counter() -> float:
        return next(timeline)

    monkeypatch.setattr('elmetron.acquisition.service.time.perf_counter', _fake_perf_counter)

    monitor.contend()
    monitor.acquired('window')
    monitor.released('window')
    monitor.acquired('window')
    monitor.released('window')

    assert stats.wait_events == 1
    assert stats.last_wait_s == 0.0
    assert stats.max_wait_s == pytest.approx(0.1)
    assert stats.average_wait_s == pytest.approx(0.1)
    assert stats.hold_events == 2
    assert stats.last_hold_s == pytest.approx(0.3)
    assert stats.max_hold_s == pytest.approx(0.35)
    assert stats.average_hold_s == pytest.approx((0.35 + 0.3) / 2)
    assert stats.current_owner is None


def test_run_retries_device_open_before_starting_session(monkeypatch) -> None:
    class FakeDatabase:
        def __init__(self) -> None:
            self.initialised = False
            self.sessions: list[FakeSessionHandle] = []

        def initialise(self) -> None:
            self.initialised = True

        def start_session(self, *_args, **_kwargs):
            handle = FakeSessionHandle()
            self.sessions.append(handle)
            return handle

    class FakeSessionHandle:
        def __init__(self) -> None:
            self.id = 1
            self.events = []
            self.closed = False

        def log_event(self, level, category, message, payload=None) -> None:
            self.events.append((level, category, message, payload))

        def close(self, *_args, **_kwargs) -> None:
            self.closed = True

    class FakeFrameIngestor:
        def __init__(self, *_args, **_kwargs) -> None:
            self.frames = 0
            self.analytics_profile = None

        def handle_frame(self, frame):
            _ = frame
            self.frames += 1
            return {}

    class TransientInterface:
        def __init__(self) -> None:
            self.open_calls = 0
            self.close_calls = 0

        def open(self):
            self.open_calls += 1
            if self.open_calls == 1:
                raise RuntimeError("device unavailable")
            return ListedDevice(index=0, serial="SER123", description="CX-505")

        def close(self) -> None:
            self.close_calls += 1

        def run_window(self, *_args, **_kwargs) -> int:
            return 0

        def write(self, *_args, **_kwargs) -> int:
            return 0

    config = AppConfig()
    config.acquisition.quiet = True
    config.acquisition.max_runtime_s = 0.05
    config.acquisition.restart_delay_s = 0.01
    config.acquisition.status_interval_s = 0.0
    config.analytics.enabled = False

    database = FakeDatabase()
    interface = TransientInterface()

    def interface_factory():
        return interface

    service = AcquisitionService(
        config,
        database=database,
        interface_factory=interface_factory,
        command_definitions={},
        use_async_commands=False,
    )

    monkeypatch.setattr("elmetron.acquisition.service.FrameIngestor", FakeFrameIngestor)
    monkeypatch.setattr("elmetron.acquisition.service.time.sleep", lambda *_: None)

    service.run()

    assert interface.open_calls >= 2
    assert database.initialised is True
    assert database.sessions
    assert database.sessions[0].closed is True
