"""Session-centric reporting utilities."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional


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
