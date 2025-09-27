"""Health/status API primitives for the acquisition service."""
from __future__ import annotations

import json
import platform
import subprocess
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional

from ..acquisition.service import AcquisitionService
from ..config import MonitoringConfig

LOG_ROTATION_TIMEOUT_S = 5


def _isoformat(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def health_status_to_dict(status: "HealthStatus") -> Dict[str, Any]:
    """Serialise a HealthStatus dataclass to basic Python types."""

    payload = asdict(status)
    payload['last_frame_at'] = _isoformat(status.last_frame_at)
    payload['last_window_started'] = _isoformat(status.last_window_started)
    return payload


def _check_log_rotation_task(task_name: str, max_age_minutes: int) -> Dict[str, Any]:
    status: Dict[str, Any] = {'name': task_name}
    if not task_name:
        status['status'] = 'disabled'
        return status
    if platform.system().lower() != 'windows':
        status['status'] = 'unsupported'
        status['message'] = 'Log rotation monitoring is only available on Windows.'
        return status
    escaped_name = task_name.replace("'", "''")
    script_lines = [
        f"$taskName = '{escaped_name}';",
        "$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue;",
        "if (-not $task) {",
        "    Write-Output '{\"state\":\"missing\"}';",
        "    exit 0;",
        "}",
        "$info = Get-ScheduledTaskInfo -TaskName $taskName;",
        "$result = [pscustomobject]@{",
        "    state = 'ok';",
        "    lastTaskResult = $info.LastTaskResult;",
        "    lastRunTime = if ($info.LastRunTime) { $info.LastRunTime.ToUniversalTime().ToString('o') } else { $null };",
        "    nextRunTime = if ($info.NextRunTime) { $info.NextRunTime.ToUniversalTime().ToString('o') } else { $null };",
        "    lastRunAgeMinutes = if ($info.LastRunTime) { [math]::Round(((Get-Date) - $info.LastRunTime).TotalMinutes, 2) } else { $null };",
        "};",
        "$result | ConvertTo-Json -Compress",
    ]
    script = '\n'.join(script_lines)
    try:
        completed = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', script],
            capture_output=True,
            text=True,
            check=False,
            timeout=LOG_ROTATION_TIMEOUT_S,
        )
    except FileNotFoundError:
        status['status'] = 'error'
        status['message'] = 'powershell.exe not available'
        return status
    except subprocess.TimeoutExpired:
        status['status'] = 'error'
        status['message'] = 'Scheduled task query timed out'
        return status

    output = (completed.stdout or '').strip()
    if completed.returncode != 0:
        status['status'] = 'error'
        status['message'] = (completed.stderr or output or '').strip() or 'Scheduled task query failed'
        return status
    if not output:
        status['status'] = 'error'
        status['message'] = 'Scheduled task query returned no data'
        return status

    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        status['status'] = 'error'
        status['message'] = 'Unable to parse scheduled task response'
        status['raw'] = output
        return status

    if payload == {'state': 'missing'} or payload.get('state') == 'missing':
        status['status'] = 'missing'
        return status

    last_result = payload.get('lastTaskResult')
    try:
        last_result_int = int(last_result) if last_result is not None else None
    except (TypeError, ValueError):
        last_result_int = None

    last_age = payload.get('lastRunAgeMinutes')
    try:
        last_age_float = float(last_age) if last_age is not None else None
    except (TypeError, ValueError):
        last_age_float = None

    threshold = max(int(max_age_minutes or 0), 0)
    within_threshold = True if threshold == 0 or last_age_float is None else last_age_float <= threshold

    status.update({
        'status': 'ok',
        'task_state': payload.get('state'),
        'last_task_result': last_result_int,
        'last_task_result_raw': last_result,
        'last_run_time': payload.get('lastRunTime'),
        'next_run_time': payload.get('nextRunTime'),
        'last_run_age_minutes': last_age_float,
        'threshold_minutes': threshold,
        'within_threshold': within_threshold,
    })

    if last_result_int not in (None, 0):
        status['status'] = 'failed'
        status['message'] = 'LastTaskResult is not success (0)'
    if within_threshold is False:
        status['status'] = 'stale'
        status['message'] = 'Log rotation task exceeded freshness threshold'

    return status


@dataclass(slots=True)
class HealthStatus:
    """Snapshot of the acquisition service health."""

    state: str
    frames: int
    bytes_read: int
    last_frame_at: Optional[datetime]
    last_window_started: Optional[datetime]
    watchdog_alert: Optional[str] = None
    detail: Optional[str] = None
    log_rotation: Optional[Dict[str, Any]] = None
    watchdog_history: Optional[List[Dict[str, Any]]] = None
    command_metrics: Optional[Dict[str, Any]] = None


class HealthMonitor:
    """Retrieve status snapshots for the UI/runtime integrations."""

    def __init__(self, service: AcquisitionService, monitoring: Optional[MonitoringConfig] = None) -> None:
        self._service = service
        self._monitoring = monitoring
        self._watchdog_alert: Optional[str] = None
        self._watchdog_detail: Optional[str] = None
        self._watchdog_events: Deque[Dict[str, Any]] = deque(maxlen=32)
        self._log_rotation_cache: Optional[Dict[str, Any]] = None
        self._log_rotation_checked_at: Optional[datetime] = None

    @property
    def service(self) -> AcquisitionService:
        """Expose the underlying acquisition service for diagnostics."""

        return self._service

    @property
    def monitoring_config(self) -> Optional[MonitoringConfig]:
        """Return the monitoring configuration, if available."""

        return self._monitoring

    def _log_rotation_status(self) -> Optional[Dict[str, Any]]:
        if not self._monitoring or not self._monitoring.log_rotation_task:
            return None
        refresh = max(int(self._monitoring.log_rotation_probe_interval_s or 0), 1)
        now = datetime.utcnow()
        if self._log_rotation_checked_at and now - self._log_rotation_checked_at < timedelta(seconds=refresh):
            return self._log_rotation_cache
        status = _check_log_rotation_task(
            self._monitoring.log_rotation_task,
            int(self._monitoring.log_rotation_max_age_minutes or 0),
        )
        self._log_rotation_cache = status
        self._log_rotation_checked_at = now
        return status

    def _command_metrics(self) -> Dict[str, Any]:
        service = self._service
        if hasattr(service, 'command_metrics'):
            try:
                return service.command_metrics()  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover - defensive guard
                return {}
        return {}

    def record_watchdog_event(
        self,
        kind: str,
        message: str,
        occurred_at: datetime,
        payload: Optional[Any] = None,
    ) -> None:
        record: Dict[str, Any] = {
            'kind': kind,
            'message': message,
            'occurred_at': occurred_at.isoformat(),
        }
        if payload is not None:
            record['payload'] = payload
        self._watchdog_events.appendleft(record)
        if kind == 'timeout':
            self._watchdog_alert = message
            if payload is None:
                self._watchdog_detail = None
            elif isinstance(payload, dict):
                try:
                    self._watchdog_detail = json.dumps(payload, ensure_ascii=False)
                except TypeError:  # pragma: no cover - non-serialisable payload
                    self._watchdog_detail = str(payload)
            else:
                self._watchdog_detail = str(payload)
        elif kind == 'recovery':
            self._watchdog_alert = None
            self._watchdog_detail = None

    def update_watchdog(self, message: str, detail: Optional[str] = None) -> None:
        payload: Optional[Dict[str, Any]] = None
        if detail is not None:
            payload = {'detail': detail}
        self.record_watchdog_event('timeout', message, datetime.utcnow(), payload)

    def clear_watchdog(self) -> None:
        self.record_watchdog_event('recovery', 'Watchdog recovered', datetime.utcnow())


    def recent_events(self, *, limit: int = 20, since_id: Optional[int] = None) -> list[Dict[str, Any]]:
        """Return recent audit events for diagnostics dashboards."""

        database = getattr(self._service, 'database', None)
        if database is None or not hasattr(database, 'recent_audit_events'):
            return []
        return database.recent_audit_events(limit=limit, since_id=since_id)

    def snapshot(self) -> HealthStatus:
        stats = self._service.stats
        state = 'running' if not self._service._stop_requested else 'stopping'  # pylint: disable=protected-access
        return HealthStatus(
            state=state,
            frames=stats.frames,
            bytes_read=stats.bytes_read,
            last_frame_at=stats.last_frame_at,
            last_window_started=stats.last_window_started,
            watchdog_alert=self._watchdog_alert,
            detail=self._watchdog_detail,
            log_rotation=self._log_rotation_status(),
            watchdog_history=list(self._watchdog_events),
            command_metrics=self._command_metrics(),
        )





