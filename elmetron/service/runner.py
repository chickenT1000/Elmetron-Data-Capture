"""Service integration helpers for supervisor/watchdog."""
from __future__ import annotations

from typing import Callable, Optional, Tuple

from ..acquisition.service import AcquisitionService
from ..api.health import HealthMonitor
from ..api.server import HealthApiServer
from ..config import MonitoringConfig
from .supervisor import ServiceSupervisor
from .watchdog import CaptureWatchdog, WatchdogEvent


class ServiceRunner:
    """Convenience wrapper binding supervisor, watchdogs, health monitor, and API."""

    def __init__(
        self,
        service: AcquisitionService,
        watchdog_timeout: float = 0.0,
        watchdog_poll: float = 2.0,
        on_watchdog_event: Optional[Callable[[WatchdogEvent], None]] = None,
        health_api_host: Optional[str] = None,
        health_api_port: int = 0,
        monitoring_config: Optional[MonitoringConfig] = None,
    ) -> None:
        self.service = service
        self.health = HealthMonitor(service, monitoring_config)
        self.supervisor = ServiceSupervisor(service)
        self._watchdog_timeout = watchdog_timeout
        self._watchdog_poll = watchdog_poll
        self._on_watchdog_event = on_watchdog_event
        self._api_server: Optional[HealthApiServer] = None

        if watchdog_timeout > 0:
            self._attach_watchdog()

        if health_api_port > 0:
            host = health_api_host or '127.0.0.1'
            self._api_server = HealthApiServer(self.health, host=host, port=health_api_port)

    @property
    def health_api_address(self) -> Optional[Tuple[str, int]]:
        if self._api_server:
            return self._api_server.address
        return None

    def _attach_watchdog(self) -> None:
        def _handle(event: WatchdogEvent) -> None:
            payload = event.payload
            self.health.record_watchdog_event(event.kind, event.message, event.occurred_at, payload)
            if self._on_watchdog_event:
                self._on_watchdog_event(event)

        watchdog = CaptureWatchdog(
            self.service,
            timeout_s=self._watchdog_timeout,
            poll_interval_s=self._watchdog_poll,
            on_event=_handle,
        )
        self.supervisor.add_watchdog(watchdog)

    def run(self) -> None:
        if self._api_server:
            self._api_server.start()
        try:
            self.supervisor.run()
        finally:
            if self._api_server:
                self._api_server.stop()

