"""Watchdog utilities for monitoring the acquisition service."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

if True:  # type-checkers only
    try:
        from ..acquisition.service import AcquisitionService
    except ImportError:  # pragma: no cover - circular import guard
        AcquisitionService = Any  # type: ignore


@dataclass(slots=True)
class WatchdogEvent:
    """Represents a lifecycle event emitted by a watchdog."""

    kind: str
    message: str
    occurred_at: datetime
    payload: Optional[dict[str, Any]] = None


class CaptureWatchdog:
    """Simple watchdog that warns when no frames arrive within *timeout_s*."""

    def __init__(
        self,
        service: 'AcquisitionService',
        timeout_s: float = 30.0,
        poll_interval_s: float = 2.0,
        on_event: Optional[Callable[[WatchdogEvent], None]] = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError('timeout_s must be positive')
        if poll_interval_s <= 0:
            raise ValueError('poll_interval_s must be positive')
        self._service = service
        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._on_event = on_event
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._alert_active = False
        self._last_frame_count = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='capture-watchdog', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _emit(self, kind: str, message: str, payload: Optional[dict[str, Any]] = None) -> None:
        if not self._on_event:
            return
        event = WatchdogEvent(kind=kind, message=message, occurred_at=datetime.now(timezone.utc), payload=payload)
        try:
            self._on_event(event)
        except Exception:  # pragma: no cover - defensive
            pass

    def _run(self) -> None:
        while not self._stop.wait(self._poll_interval_s):
            stats = self._service.stats
            frames = stats.frames
            last_frame_at = stats.last_frame_at
            now = datetime.utcnow()

            if frames > self._last_frame_count:
                self._last_frame_count = frames
                if self._alert_active:
                    self._alert_active = False
                    self._emit(
                        'recovery',
                        'Frames received after watchdog timeout',
                        {
                            'frames': frames,
                            'bytes_read': stats.bytes_read,
                        },
                    )
                continue

            if frames == 0 and last_frame_at is None:
                last_window = stats.last_window_started
                if last_window is None:
                    continue
                elapsed = (now - last_window).total_seconds()
            elif last_frame_at is not None:
                elapsed = (now - last_frame_at).total_seconds()
            else:
                elapsed = 0.0

            if elapsed >= self._timeout_s and not self._alert_active:
                self._alert_active = True
                self._emit(
                    'timeout',
                    'No frames observed within watchdog timeout',
                    {
                        'elapsed_s': elapsed,
                        'frames': frames,
                        'bytes_read': stats.bytes_read,
                    },
                )

