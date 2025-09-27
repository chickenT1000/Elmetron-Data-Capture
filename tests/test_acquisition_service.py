from __future__ import annotations

from typing import List

import time

import pytest

from elmetron.acquisition.service import AcquisitionService
from elmetron.commands.executor import CommandDefinition, CommandResult
from elmetron.config import AppConfig, ScheduledCommandConfig


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


@pytest.fixture()
def base_service() -> AcquisitionService:
    config = AppConfig()
    config.acquisition.startup_commands = ['run_ok', 'missing', 'run_fail']
    config.acquisition.quiet = True
    config.device.profile = 'cx505'

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

def test_scheduled_command_runs_on_startup_with_retry() -> None:
    config = AppConfig()
    config.acquisition.startup_commands = []
    config.acquisition.quiet = True
    config.device.profile = 'cx505'
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
