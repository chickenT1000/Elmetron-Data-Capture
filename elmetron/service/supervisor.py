"""Service supervisor coordinates acquisition and watchdogs."""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from typing import Iterable, List, Optional

from ..acquisition.service import AcquisitionService
from .watchdog import CaptureWatchdog, WatchdogEvent


@dataclass(slots=True)
class SupervisorOptions:
    """Configuration options for the service supervisor."""

    start_watchdogs: bool = True


class ServiceSupervisor:
    """Wrapper around :class:`AcquisitionService` that manages watchdogs."""

    def __init__(
        self,
        service: AcquisitionService,
        watchdogs: Optional[Iterable[CaptureWatchdog]] = None,
        options: Optional[SupervisorOptions] = None,
    ) -> None:
        self._service = service
        self._watchdogs: List[CaptureWatchdog] = list(watchdogs or [])
        self._options = options or SupervisorOptions()

    @property
    def service(self) -> AcquisitionService:
        return self._service

    def add_watchdog(self, watchdog: CaptureWatchdog) -> None:
        self._watchdogs.append(watchdog)

    def run(self) -> None:
        """Run the acquisition service while managing watchdog lifecycle."""

        with ExitStack() as stack:
            if self._options.start_watchdogs:
                for watchdog in self._watchdogs:
                    watchdog.start()
                    stack.callback(watchdog.stop)
            self._service.run()

    @staticmethod
    def default_watchdog_handler(event: WatchdogEvent) -> None:
        """Basic handler that prints the watchdog event."""

        timestamp = event.occurred_at.isoformat()
        payload = f" payload={event.payload}" if event.payload else ""
        print(f"[watchdog] {timestamp} {event.kind}: {event.message}{payload}")


