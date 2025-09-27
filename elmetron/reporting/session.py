"""Session-centric reporting utilities."""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

from ..storage.database import Database


def iter_session_measurements(database: Path, session_id: int) -> Iterator[Dict[str, object]]:
    """Yield decoded measurement records for *session_id* from *database*."""

    conn = sqlite3.connect(str(database))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            """
            SELECT m.id AS measurement_id,
                   m.frame_id,
                   m.session_id,
                   m.measurement_timestamp,
                   m.value,
                   m.unit,
                   m.temperature,
                   m.temperature_unit,
                   rf.captured_at,
                   rf.frame_hex,
                   m.payload_json,
                   dm.metrics_json
            FROM measurements AS m
            JOIN raw_frames AS rf ON rf.id = m.frame_id
            LEFT JOIN derived_metrics AS dm ON dm.measurement_id = m.id
            WHERE m.session_id = ?
            ORDER BY m.id
            """,
            (session_id,),
        )
        for row in cursor:
            payload = json.loads(row['payload_json'])
            metrics_json = row['metrics_json'] if 'metrics_json' in row.keys() else None
            metrics = json.loads(metrics_json) if metrics_json else None
            record = {
                'measurement_id': row['measurement_id'],
                'frame_id': row['frame_id'],
                'session_id': row['session_id'],
                'measurement_timestamp': row['measurement_timestamp'],
                'captured_at': row['captured_at'],
                'value': row['value'],
                'unit': row['unit'],
                'temperature': row['temperature'],
                'temperature_unit': row['temperature_unit'],
                'frame_hex': row['frame_hex'],
                'payload': payload,
            }
            if metrics is not None:
                record['analytics'] = metrics
            yield record
    finally:
        conn.close()


def load_session_summary(database: Path, session_id: int) -> Optional[Dict[str, object]]:
    """Return a high-level summary for *session_id* or ``None`` if missing."""

    conn = sqlite3.connect(str(database))
    conn.row_factory = sqlite3.Row
    try:
        session = conn.execute(
            "SELECT id, instrument_id, started_at, ended_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            return None
        instrument = conn.execute(
            "SELECT serial, description, model FROM instruments WHERE id = ?",
            (session['instrument_id'],),
        ).fetchone()
        meta_rows = conn.execute(
            "SELECT key, value FROM session_metadata WHERE session_id = ? ORDER BY key",
            (session_id,),
        ).fetchall()
        metadata = {row['key']: row['value'] for row in meta_rows}
        counts = conn.execute(
            "SELECT COUNT(*) AS measurements, MAX(created_at) AS last_recorded FROM measurements WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return {
            'session_id': session['id'],
            'started_at': session['started_at'],
            'ended_at': session['ended_at'],
            'instrument': dict(instrument) if instrument else None,
            'metadata': metadata,
            'measurements': counts['measurements'] if counts else 0,
            'last_recorded_at': counts['last_recorded'] if counts else None,
        }
    finally:
        conn.close()


def _coerce_database_path(database: Union[Path, Database, str]) -> Path:
    if isinstance(database, Database):
        return database.path
    if isinstance(database, Path):
        return database
    return Path(database)


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith('Z'):
        candidate = candidate[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
            try:
                dt = datetime.strptime(candidate, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _is_calibration_record(record: Dict[str, Any]) -> bool:
    payload = record.get('payload')
    if isinstance(payload, dict):
        measurement = payload.get('measurement')
        if isinstance(measurement, dict):
            mode = measurement.get('mode')
            if isinstance(mode, str) and 'calib' in mode.lower():
                return True
        for key, value in payload.items():
            if isinstance(key, str) and 'calib' in key.lower():
                return True
            if isinstance(value, str) and 'calib' in value.lower():
                return True
    analytics = record.get('analytics')
    if isinstance(analytics, dict):
        for key, value in analytics.items():
            if isinstance(key, str) and 'calib' in key.lower():
                return True
            if isinstance(value, str) and 'calib' in value.lower():
                return True
            if isinstance(value, dict):
                for nested_value in value.values():
                    if isinstance(nested_value, str) and 'calib' in nested_value.lower():
                        return True
    return False


def _resolve_anchor(records: List[Dict[str, Any]], preferred: str) -> Tuple[str, Optional[datetime]]:
    timestamps: List[Tuple[str, Optional[datetime], Dict[str, Any]]] = []
    for record in records:
        measurement_ts = record.get('measurement_timestamp')
        captured_at = record.get('captured_at')
        ts = _parse_timestamp(measurement_ts) or _parse_timestamp(captured_at)
        timestamps.append((record.get('measurement_id'), ts, record))
    if not timestamps:
        return 'start', None

    if preferred == 'calibration':
        for _, ts, record in timestamps:
            if ts and _is_calibration_record(record):
                return 'calibration', ts

    for _, ts, _ in timestamps:
        if ts:
            return 'start', ts
    return 'start', None


def _numeric_series(values: Iterable[Any]) -> List[float]:
    series: List[float] = []
    for value in values:
        if isinstance(value, (int, float)):
            candidate = float(value)
            if math.isfinite(candidate):
                series.append(candidate)
    return series


def _aggregate(values: Iterable[Any]) -> Dict[str, Any]:
    series = _numeric_series(values)
    if not series:
        return {'min': None, 'max': None, 'average': None, 'samples': 0}
    return {
        'min': min(series),
        'max': max(series),
        'average': mean(series),
        'samples': len(series),
    }


def build_session_evaluation(
    database: Union[Path, Database, str],
    session_id: int,
    *,
    anchor: str = 'start',
) -> Optional[Dict[str, Any]]:
    db_path = _coerce_database_path(database)
    summary = load_session_summary(db_path, session_id)
    if summary is None:
        return None
    records = list(iter_session_measurements(db_path, session_id))
    anchor_label = anchor if anchor in {'start', 'calibration'} else 'start'
    anchor_label, anchor_ts = _resolve_anchor(records, anchor_label)

    series: List[Dict[str, Any]] = []
    markers: List[Dict[str, Any]] = []
    offsets: List[float] = []
    for record in records:
        measurement_ts = record.get('measurement_timestamp') or record.get('captured_at')
        timestamp = _parse_timestamp(measurement_ts) if isinstance(measurement_ts, str) else None
        offset_seconds: Optional[float] = None
        if timestamp and anchor_ts:
            offset_seconds = (timestamp - anchor_ts).total_seconds()
            offsets.append(offset_seconds)
        payload = record.get('payload')
        analytics = record.get('analytics')
        entry: Dict[str, Any] = {
            'measurement_id': record.get('measurement_id'),
            'frame_id': record.get('frame_id'),
            'timestamp': measurement_ts,
            'captured_at': record.get('captured_at'),
            'offset_seconds': offset_seconds,
            'value': record.get('value'),
            'unit': record.get('unit'),
            'temperature': record.get('temperature'),
            'temperature_unit': record.get('temperature_unit'),
            'payload': payload,
        }
        if analytics is not None:
            entry['analytics'] = analytics
        series.append(entry)

        if _is_calibration_record(record):
            markers.append({
                'type': 'calibration',
                'timestamp': measurement_ts,
                'offset_seconds': offset_seconds,
                'measurement_id': record.get('measurement_id'),
            })

    duration_seconds = None
    if offsets:
        duration_seconds = max(offsets) - min(offsets)

    value_stats = _aggregate(entry.get('value') for entry in series)
    value_stats['unit'] = series[0].get('unit') if series else None
    temperature_stats = _aggregate(entry.get('temperature') for entry in series)
    temperature_stats['unit'] = series[0].get('temperature_unit') if series else None

    statistics = {
        'value': value_stats,
        'temperature': temperature_stats,
    }

    return {
        'session': summary,
        'anchor': anchor_label,
        'anchor_timestamp': anchor_ts.isoformat() if anchor_ts else None,
        'series': series,
        'markers': markers,
        'statistics': statistics,
        'duration_seconds': duration_seconds,
        'samples': len(series),
    }
