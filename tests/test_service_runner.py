from __future__ import annotations

import socket
import threading
import time
from datetime import datetime

from elmetron.acquisition.service import ServiceStats
from elmetron.service.runner import ServiceRunner


class _DummyService:
    def __init__(self) -> None:
        self.stats = ServiceStats(last_window_started=datetime.utcnow())
        self._stop_requested = False
        self.started = threading.Event()
        self._stop_signal = threading.Event()

    def run(self) -> None:
        self.started.set()
        try:
            self._stop_signal.wait(timeout=0.5)
        finally:
            self._stop_requested = True

    def request_stop(self) -> None:
        self._stop_signal.set()


def _wait_for(predicate, timeout=1.0, interval=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _thread_by_name(name: str):
    for thread in threading.enumerate():
        if thread.name == name:
            return thread
    return None


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_service_runner_starts_and_stops_watchdog_and_health_api():
    service = _DummyService()
    port = _get_free_port()
    runner = ServiceRunner(
        service,
        watchdog_timeout=0.1,
        watchdog_poll=0.05,
        health_api_host='127.0.0.1',
        health_api_port=port,
    )

    address = runner.health_api_address
    assert address == ('127.0.0.1', port)

    runner_thread = threading.Thread(target=runner.run, daemon=True)
    runner_thread.start()

    assert service.started.wait(timeout=1.0)
    assert _wait_for(lambda: _thread_by_name('capture-watchdog') is not None, timeout=1.0)

    api_server = runner._api_server  # type: ignore[attr-defined]
    assert api_server is not None
    assert _wait_for(
        lambda: getattr(api_server, '_thread', None) is not None
        and getattr(api_server, '_thread').is_alive(),
        timeout=1.0,
    )

    service.request_stop()
    runner_thread.join(timeout=2.0)
    assert not runner_thread.is_alive()

    assert _wait_for(lambda: _thread_by_name('capture-watchdog') is None, timeout=1.0)

    api_thread = getattr(api_server, '_thread', None)
    if api_thread is not None:
        assert _wait_for(lambda: not api_thread.is_alive(), timeout=1.0)
