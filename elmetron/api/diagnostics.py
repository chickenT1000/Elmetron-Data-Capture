"""Diagnostic bundle generator for the health API."""
from __future__ import annotations

import io
import json
import platform
import sys
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..acquisition.service import AcquisitionService
from ..protocols import CommandDefinition
from .health import HealthMonitor, health_status_to_dict


_MAX_EVENT_LIMIT = 1000
_MAX_SESSION_LIMIT = 100


def _isoformat(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')


def _config_payload(config: Optional[Any]) -> Optional[Dict[str, Any]]:
    if config is None:
        return None
    try:
        to_dict = getattr(config, 'to_dict', None)
        if callable(to_dict):
            return to_dict()
        return asdict(config)
    except Exception:  # pragma: no cover - defensive guard
        return None


def _command_definitions_payload(definitions: Dict[str, CommandDefinition]) -> Dict[str, Dict[str, Any]]:
    bundle: Dict[str, Dict[str, Any]] = {}
    for name, definition in definitions.items():
        try:
            bundle[name] = asdict(definition)
        except TypeError:  # pragma: no cover - dataclass mismatch
            bundle[name] = {
                'name': getattr(definition, 'name', name),
                'description': getattr(definition, 'description', None),
                'category': getattr(definition, 'category', None),
            }
    return bundle


def _command_metrics_payload(service: AcquisitionService) -> Dict[str, Any]:
    try:
        return service.command_metrics()
    except Exception:  # pragma: no cover - defensive
        return {}


def _stats_payload(service: AcquisitionService) -> Dict[str, Any]:
    stats = service.stats
    return {
        'frames': stats.frames,
        'bytes_read': stats.bytes_read,
        'last_window_bytes': stats.last_window_bytes,
        'last_window_started': _isoformat(stats.last_window_started),
        'last_frame_at': _isoformat(stats.last_frame_at),
    }


def _sessions_payload(service: AcquisitionService, limit: int) -> Dict[str, Any]:
    database = service.database
    try:
        sessions = database.recent_sessions(limit=limit)
    except Exception as exc:  # pragma: no cover - surfaced in payload
        return {
            'database_path': str(database.path),
            'error': str(exc),
            'sessions': [],
        }
    return {
        'database_path': str(database.path),
        'sessions': sessions,
    }


def _environment_payload() -> Dict[str, Any]:
    return {
        'python_version': sys.version,
        'platform': platform.platform(),
        'executable': sys.executable,
        'cwd': str(Path.cwd()),
    }


def build_diagnostic_bundle(
    service: AcquisitionService,
    monitor: HealthMonitor,
    *,
    event_limit: int = 200,
    session_limit: int = 5,
) -> bytes:
    """Return a ZIP archive capturing health, config, and recent activity."""

    event_limit = max(1, min(event_limit, _MAX_EVENT_LIMIT))
    session_limit = max(0, min(session_limit, _MAX_SESSION_LIMIT))

    generated_at = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    snapshot = health_status_to_dict(monitor.snapshot())
    try:
        events = monitor.recent_events(limit=event_limit)
    except Exception:  # pragma: no cover - fallback to empty list
        events = []

    config = getattr(service, '_config', None)
    command_definitions = getattr(service, '_command_definitions', {})
    monitoring_config = monitor.monitoring_config

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        sessions_payload = _sessions_payload(service, limit=session_limit)

        manifest = {
            'generated_at': generated_at,
            'tool': 'elmetron-diagnostic-bundle',
            'version': '1.0',
            'counts': {
                'events': len(events),
                'sessions': len(sessions_payload.get('sessions', [])),
            },
            'context': {
                'database_path': sessions_payload.get('database_path'),
                'config_available': bool(config),
            },
            'files': {
                'health_snapshot': 'health/snapshot.json',
                'log_events': 'health/log_events.json',
                'service_stats': 'service/stats.json',
                'command_metrics': 'service/command_metrics.json',
                'environment': 'service/environment.json',
                'config': 'config/app_config.json',
                'monitoring': 'config/monitoring.json',
                'commands': 'config/command_definitions.json',
                'sessions': 'storage/recent_sessions.json',
            },
        }
        archive.writestr('manifest.json', _json_bytes(manifest))
        archive.writestr('health/snapshot.json', _json_bytes(snapshot))
        archive.writestr('health/log_events.json', _json_bytes(events))
        archive.writestr('service/stats.json', _json_bytes(_stats_payload(service)))
        archive.writestr('service/command_metrics.json', _json_bytes(_command_metrics_payload(service)))
        archive.writestr('service/environment.json', _json_bytes(_environment_payload()))
        archive.writestr('config/app_config.json', _json_bytes(_config_payload(config)))
        monitoring_payload = asdict(monitoring_config) if monitoring_config else None
        archive.writestr('config/monitoring.json', _json_bytes(monitoring_payload))
        archive.writestr('config/command_definitions.json', _json_bytes(_command_definitions_payload(command_definitions)))
        archive.writestr('storage/recent_sessions.json', _json_bytes(sessions_payload))

    return bundle.getvalue()
