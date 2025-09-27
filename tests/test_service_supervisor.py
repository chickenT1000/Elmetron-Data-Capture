from __future__ import annotations

import pytest

from elmetron.service.supervisor import ServiceSupervisor, SupervisorOptions


class _StubWatchdog:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        if self.started:
            raise AssertionError('start called twice')
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class _StubService:
    def __init__(self, *, raises: bool = False) -> None:
        self.run_calls = 0
        self.raises = raises

    def run(self) -> None:
        self.run_calls += 1
        if self.raises:
            raise RuntimeError('boom')


def test_service_supervisor_runs_watchdogs_and_service() -> None:
    service = _StubService()
    watchdogs = [_StubWatchdog(), _StubWatchdog()]

    supervisor = ServiceSupervisor(service, watchdogs)
    supervisor.run()

    assert service.run_calls == 1
    assert all(w.started for w in watchdogs)
    assert all(w.stopped for w in watchdogs)


def test_service_supervisor_stops_watchdogs_on_failure() -> None:
    service = _StubService(raises=True)
    watchdogs = [_StubWatchdog(), _StubWatchdog()]
    supervisor = ServiceSupervisor(service, watchdogs)

    with pytest.raises(RuntimeError):
        supervisor.run()

    assert service.run_calls == 1
    assert all(w.started for w in watchdogs)
    assert all(w.stopped for w in watchdogs)


def test_service_supervisor_respects_start_watchdogs_flag() -> None:
    service = _StubService()
    watchdog = _StubWatchdog()
    supervisor = ServiceSupervisor(
        service,
        [watchdog],
        options=SupervisorOptions(start_watchdogs=False),
    )

    supervisor.run()

    assert service.run_calls == 1
    assert not watchdog.started
    assert not watchdog.stopped
