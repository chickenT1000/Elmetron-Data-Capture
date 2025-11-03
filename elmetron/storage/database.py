"""SQLite persistence layer for Elmetron capture sessions."""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import StorageConfig


@dataclass(slots=True)
class DeviceMetadata:
    serial: Optional[str]
    description: Optional[str]
    model: Optional[str]


@dataclass(slots=True)
class StoredMeasurement:
    frame_id: int
    measurement_id: int


@dataclass(slots=True)
class AuditEvent:
    level: str
    category: str
    message: str
    payload: Optional[Dict[str, Any]] = None


class Database:
    """High-level wrapper around the project SQLite schema."""

    def __init__(self, config: StorageConfig):
        self._config = config
        self._path = config.database_path.expanduser()
        if config.ensure_directories:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def path(self) -> Path:
        return self._path

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(str(self._path))
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def initialise(self) -> None:
        conn = self.connect()
        with conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS instruments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial TEXT UNIQUE,
                    description TEXT,
                    model TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_id INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(instrument_id) REFERENCES instruments(id)
                );
                CREATE TABLE IF NOT EXISTS session_metadata (
                    session_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(session_id, key),
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS raw_frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    captured_at TEXT NOT NULL,
                    frame_hex TEXT NOT NULL,
                    frame_bytes BLOB NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    frame_id INTEGER NOT NULL,
                    measurement_timestamp TEXT,
                    value REAL,
                    unit TEXT,
                    temperature REAL,
                    temperature_unit TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(frame_id) REFERENCES raw_frames(id)
                );
                CREATE TABLE IF NOT EXISTS annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    measurement_id INTEGER NOT NULL,
                    author TEXT,
                    body TEXT,
                    tags TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(measurement_id) REFERENCES measurements(id)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'backend',
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS derived_metrics (
                    measurement_id INTEGER PRIMARY KEY,
                    metrics_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(measurement_id) REFERENCES measurements(id)
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_instrument ON sessions(instrument_id);
                CREATE INDEX IF NOT EXISTS idx_raw_frames_session ON raw_frames(session_id);
                CREATE INDEX IF NOT EXISTS idx_measurements_session ON measurements(session_id);
                CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON measurements(measurement_timestamp);
                CREATE INDEX IF NOT EXISTS idx_session_metadata_session ON session_metadata(session_id);
                CREATE INDEX IF NOT EXISTS idx_audit_events_session ON audit_events(session_id);
                """
            )
            self._apply_migrations(conn)
        if self._config.vacuum_on_start:
            with conn:
                conn.execute('VACUUM')
        if self._config.retention_days:
            self.apply_retention(datetime.utcnow())

    def apply_retention(self, now: datetime) -> None:
        """Apply retention policies.
        
        NOTE: This now ONLY deletes old system logs, NOT session data!
        Session data retention should be managed separately by users.
        
        System logs older than retention_days are deleted to prevent unbounded growth.
        Session data (measurements, frames, etc.) is preserved.
        """
        if not self._config.retention_days or self._config.retention_days <= 0:
            return
        
        # ONLY delete old system logs (session_id IS NULL)
        # Do NOT delete session data - that's user data!
        cutoff = now - timedelta(days=self._config.retention_days)
        conn = self.connect()
        cutoff_iso = cutoff.isoformat()
        
        deleted_system_logs = 0
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM audit_events 
                WHERE session_id IS NULL 
                AND created_at < ?
                """,
                (cutoff_iso,),
            )
            deleted_system_logs = cursor.rowcount
        
        # Log retention cleanup if any system logs were deleted
        if deleted_system_logs > 0:
            self.append_system_audit_event(
                AuditEvent(
                    level='info',
                    category='retention',
                    message=f'Deleted {deleted_system_logs} old system log events',
                    payload={
                        'cutoff_date': cutoff_iso,
                        'retention_days': self._config.retention_days,
                        'deleted_system_logs': deleted_system_logs,
                        'note': 'Session data preserved - only system logs deleted'
                    }
                ),
                source='backend'
            )
        
        # Session data deletion removed - handled separately by user
        # All code below this point is now unused/dead code for session deletion
    
    def _apply_session_retention_UNUSED(self, now: datetime) -> None:
        """UNUSED: Old session deletion code - kept for reference only.
        
        This was the old retention that deleted sessions. 
        Now disabled to preserve user data.
        """
        def _initial_summary() -> Dict[str, Any]:
            return {
                'session_id': None,
                'removed_measurements': 0,
                'removed_frames': 0,
                'removed_derived_metrics': 0,
                'removed_annotations': 0,
                'removed_metadata': 0,
                'removed_audit_events': 0,
                'session_deleted': False,
            }

        summaries = defaultdict(_initial_summary)

        with conn:
            measurement_rows = conn.execute(
                """
                SELECT session_id, COUNT(*) AS removed
                FROM measurements
                WHERE measurement_timestamp IS NOT NULL AND measurement_timestamp < ?
                GROUP BY session_id
                """,
                (cutoff_iso,),
            ).fetchall()
            for row in measurement_rows:
                session_id = int(row['session_id'])
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['removed_measurements'] = int(row['removed'])

            derived_rows = conn.execute(
                """
                SELECT m.session_id, COUNT(dm.measurement_id) AS removed
                FROM derived_metrics dm
                JOIN measurements m ON m.id = dm.measurement_id
                WHERE m.measurement_timestamp IS NOT NULL AND m.measurement_timestamp < ?
                GROUP BY m.session_id
                """,
                (cutoff_iso,),
            ).fetchall()
            for row in derived_rows:
                session_id = int(row['session_id'])
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['removed_derived_metrics'] = int(row['removed'])

            annotation_rows = conn.execute(
                """
                SELECT m.session_id, COUNT(a.id) AS removed
                FROM annotations a
                JOIN measurements m ON m.id = a.measurement_id
                WHERE m.measurement_timestamp IS NOT NULL AND m.measurement_timestamp < ?
                GROUP BY m.session_id
                """,
                (cutoff_iso,),
            ).fetchall()
            for row in annotation_rows:
                session_id = int(row['session_id'])
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['removed_annotations'] = int(row['removed'])

            frame_rows = conn.execute(
                """
                SELECT session_id, COUNT(*) AS removed
                FROM raw_frames
                WHERE captured_at < ?
                GROUP BY session_id
                """,
                (cutoff_iso,),
            ).fetchall()
            for row in frame_rows:
                session_id = int(row['session_id'])
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['removed_frames'] = int(row['removed'])

            # Find old sessions to delete (use started_at, not ended_at)
            # This ensures even sessions that were never properly closed get deleted
            ended_session_rows = conn.execute(
                "SELECT id FROM sessions WHERE started_at < ?",
                (cutoff_iso,),
            ).fetchall()
            ended_session_ids = {int(row['id']) for row in ended_session_rows}
            for session_id in ended_session_ids:
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['session_deleted'] = True

            metadata_rows = conn.execute(
                """
                SELECT session_id, COUNT(*) AS removed
                FROM session_metadata
                WHERE session_id IN (
                    SELECT id FROM sessions WHERE started_at < ?
                )
                GROUP BY session_id
                """,
                (cutoff_iso,),
            ).fetchall()
            for row in metadata_rows:
                session_id = int(row['session_id'])
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['removed_metadata'] = int(row['removed'])

            audit_rows = conn.execute(
                """
                SELECT session_id, COUNT(*) AS removed
                FROM audit_events
                WHERE session_id IN (
                    SELECT id FROM sessions WHERE started_at < ?
                )
                GROUP BY session_id
                """,
                (cutoff_iso,),
            ).fetchall()
            for row in audit_rows:
                session_id = int(row['session_id'])
                summary = summaries[session_id]
                if summary['session_id'] is None:
                    summary['session_id'] = session_id
                summary['removed_audit_events'] = int(row['removed'])

            if not summaries and not frame_rows and not ended_session_ids:
                return

            conn.execute(
                """
                DELETE FROM derived_metrics
                WHERE measurement_id IN (
                    SELECT id FROM measurements
                    WHERE measurement_timestamp IS NOT NULL AND measurement_timestamp < ?
                )
                """,
                (cutoff_iso,),
            )
            conn.execute(
                """
                DELETE FROM annotations
                WHERE measurement_id IN (
                    SELECT id FROM measurements
                    WHERE measurement_timestamp IS NOT NULL AND measurement_timestamp < ?
                )
                """,
                (cutoff_iso,),
            )
            conn.execute(
                "DELETE FROM measurements WHERE measurement_timestamp IS NOT NULL AND measurement_timestamp < ?",
                (cutoff_iso,),
            )
            conn.execute(
                "DELETE FROM raw_frames WHERE captured_at < ?",
                (cutoff_iso,),
            )
            conn.execute(
                "DELETE FROM session_metadata WHERE session_id IN (SELECT id FROM sessions WHERE started_at < ?)",
                (cutoff_iso,),
            )
            conn.execute(
                "DELETE FROM audit_events WHERE session_id IN (SELECT id FROM sessions WHERE started_at < ?)",
                (cutoff_iso,),
            )
            if ended_session_ids:
                conn.executemany(
                    "DELETE FROM sessions WHERE id = ?",
                    ((session_id,) for session_id in ended_session_ids),
                )

            retention_entries = [
                {
                    key: value
                    for key, value in summary.items()
                    if not (key == 'session_id' and value is None)
                }
                for summary in summaries.values()
            ]
            retention_entries = [entry for entry in retention_entries if entry.get('session_id') is not None]

            retention_entries.sort(key=lambda item: item.get('session_id') or 0)

            # Log retention cleanup (using new system event logging)
            deleted_sessions = len([e for e in retention_entries if e.get('session_id') is not None])
            total_deleted_system_logs = deleted_system_logs  # From earlier deletion
            
            if deleted_sessions > 0 or total_deleted_system_logs > 0:
                payload = {
                    'cutoff_date': cutoff_iso,
                    'retention_days': self._config.retention_days,
                }
                if deleted_sessions > 0:
                    payload['deleted_sessions'] = deleted_sessions
                    payload['session_details'] = retention_entries
                if total_deleted_system_logs > 0:
                    payload['deleted_system_logs'] = total_deleted_system_logs
                
                # Use system event logging (not tied to retention session)
                self.append_system_audit_event(
                    AuditEvent(
                        level='info',
                        category='retention',
                        message=f'Applied retention policy: {deleted_sessions} sessions, {total_deleted_system_logs} system logs',
                        payload=payload
                    ),
                    source='backend'
                )

    def start_session(
        self,
        started_at: datetime,
        metadata: DeviceMetadata,
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> "SessionHandle":
        conn = self.connect()
        instrument_id = self._ensure_instrument(conn, metadata)
        with conn:
            cursor = conn.execute(
                "INSERT INTO sessions (instrument_id, started_at) VALUES (?, ?)",
                (instrument_id, started_at.isoformat()),
            )
            session_id = cursor.lastrowid
        handle = SessionHandle(self, session_id, instrument_id, metadata)
        if session_metadata:
            handle.set_metadata(session_metadata)
        return handle

    def set_session_metadata(self, session_id: int, items: Dict[str, Any]) -> None:
        if not items:
            return
        entries = {key: _stringify(value) for key, value in items.items() if key}
        if not entries:
            return
        conn = self.connect()
        with conn:
            for key, value in entries.items():
                conn.execute(
                    """
                    INSERT INTO session_metadata (session_id, key, value)
                    VALUES (?, ?, ?)
                    ON CONFLICT(session_id, key)
                    DO UPDATE SET value = excluded.value, created_at = CURRENT_TIMESTAMP
                    """,
                    (session_id, key, value),
                )

    def set_derived_metrics(self, measurement_id: int, metrics: Dict[str, Any]) -> None:
        """Insert or update derived metrics for a measurement."""

        if not metrics:
            return
        conn = self.connect()
        payload = json.dumps(metrics, ensure_ascii=False)
        with conn:
            conn.execute(
                """
                INSERT INTO derived_metrics (measurement_id, metrics_json)
                VALUES (?, ?)
                ON CONFLICT(measurement_id)
                DO UPDATE SET metrics_json = excluded.metrics_json, created_at = CURRENT_TIMESTAMP
                """,
                (measurement_id, payload),
            )


    def append_audit_event(self, session_id: Optional[int], event: AuditEvent, source: str = 'backend') -> None:
        """Log event (session-specific or system-wide).
        
        Args:
            session_id: Session ID for session-specific events, or None for system events
            event: AuditEvent to log
            source: Source of the event ('backend', 'launcher', 'api')
        
        Note:
            DEBUG level events are NOT saved to database to prevent spam.
            Only INFO and above are persisted.
        """
        # Filter out DEBUG logs - don't save to database
        if event.level.upper() == 'DEBUG':
            return
        
        conn = self.connect()
        payload_json = None
        if event.payload is not None:
            payload_json = json.dumps(event.payload, ensure_ascii=False)
        with conn:
            conn.execute(
                """
                INSERT INTO audit_events (session_id, level, category, message, payload_json, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, event.level, event.category, event.message, payload_json, source),
            )
    
    def append_system_audit_event(self, event: AuditEvent, source: str = 'backend') -> None:
        """Log system-wide event (not tied to any session).
        
        Args:
            event: AuditEvent to log
            source: Source of the event ('backend', 'launcher', 'api')
        """
        self.append_audit_event(None, event, source)


    def recent_audit_events(
        self,
        *,
        limit: int = 20,
        since_id: Optional[int] = None,
        level: Optional[str] = None,
        session_id: Optional[int] = None,
        system_only: bool = False
    ) -> list[Dict[str, Any]]:
        """Return the most recent audit events for dashboards/diagnostics.
        
        Args:
            limit: Maximum number of events to return
            since_id: Only return events with id > since_id
            level: Filter by minimum log level (INFO, WARNING, ERROR, etc.)
                   If provided, filters out levels below it (e.g., INFO filters out DEBUG)
            session_id: Filter by specific session ID (None = all)
            system_only: If True, only return system events (session_id IS NULL)
        """

        try:
            limit_value = int(limit)
        except (TypeError, ValueError):
            limit_value = 20
        limit_value = max(1, min(limit_value, 500))

        query = ["SELECT id, session_id, level, category, message, payload_json, created_at, source FROM audit_events"]
        where_clauses: list[str] = []
        params: list[Any] = []
        
        # Filter by minimum level (exclude DEBUG if level is INFO or higher)
        if level:
            level_upper = level.upper()
            if level_upper == 'INFO':
                # INFO and above: exclude DEBUG
                where_clauses.append("UPPER(level) != 'DEBUG'")
            elif level_upper == 'WARNING':
                # WARNING and above
                where_clauses.append("UPPER(level) IN ('WARNING', 'ERROR', 'CRITICAL')")
            elif level_upper == 'ERROR':
                # ERROR and above
                where_clauses.append("UPPER(level) IN ('ERROR', 'CRITICAL')")
            elif level_upper == 'CRITICAL':
                # CRITICAL only
                where_clauses.append("UPPER(level) = 'CRITICAL'")
        
        # Filter by session
        if system_only:
            where_clauses.append("session_id IS NULL")
        elif session_id is not None:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        
        if since_id is not None:
            try:
                since_value = int(since_id)
            except (TypeError, ValueError):
                since_value = None
            else:
                where_clauses.append('id > ?')
                params.append(since_value)

        if where_clauses:
            query.append('WHERE ' + ' AND '.join(where_clauses))

        query.append('ORDER BY id DESC')
        query.append('LIMIT ?')
        params.append(limit_value)

        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(' '.join(query), params).fetchall()
        finally:
            conn.close()

        events: list[Dict[str, Any]] = []
        for row in rows:
            payload_json = row['payload_json']
            payload = json.loads(payload_json) if payload_json else None
            events.append({
                'id': row['id'],
                'session_id': row['session_id'],
                'level': row['level'],
                'category': row['category'],
                'message': row['message'],
                'payload': payload,
                'created_at': row['created_at'],
                'source': row['source'] if 'source' in row.keys() else 'backend',  # Handle old rows
            })
        return events

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        row = conn.execute('PRAGMA user_version').fetchone()
        current_version = int(row[0]) if row is not None else 0
        if current_version < 1:
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_measurements_session_timestamp
                    ON measurements(session_id, measurement_timestamp);
                CREATE INDEX IF NOT EXISTS idx_raw_frames_session_captured_at
                    ON raw_frames(session_id, captured_at);
                """
            )
            conn.execute('PRAGMA user_version = 1')

    def recent_sessions(
        self,
        *,
        limit: int = 5,
    ) -> list[Dict[str, Any]]:
        """Return the most recent sessions with lightweight statistics."""

        try:
            limit_value = int(limit)
        except (TypeError, ValueError):
            limit_value = 5
        limit_value = max(0, min(limit_value, 100))

        query = """
            SELECT
                s.id,
                s.started_at,
                s.ended_at,
                s.note,
                i.serial AS instrument_serial,
                i.description AS instrument_description,
                i.model AS instrument_model,
                (
                    SELECT COUNT(*) FROM measurements m WHERE m.session_id = s.id
                ) AS measurement_count,
                (
                    SELECT COUNT(*) FROM raw_frames f WHERE f.session_id = s.id
                ) AS frame_count,
                (
                    SELECT COUNT(*) FROM audit_events a WHERE a.session_id = s.id
                ) AS audit_count
            FROM sessions s
            LEFT JOIN instruments i ON s.instrument_id = i.id
            ORDER BY s.id DESC
            LIMIT ?
        """

        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(query, (limit_value,)).fetchall()
            sessions: list[Dict[str, Any]] = []
            for row in rows:
                metadata_rows = conn.execute(
                    "SELECT key, value FROM session_metadata WHERE session_id = ?",
                    (row['id'],),
                ).fetchall()
                metadata = {meta['key']: meta['value'] for meta in metadata_rows}
                last_measurement = conn.execute(
                    """
                    SELECT measurement_timestamp
                    FROM measurements
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (row['id'],),
                ).fetchone()
                sessions.append(
                    {
                        'id': row['id'],
                        'started_at': row['started_at'],
                        'ended_at': row['ended_at'],
                        'note': row['note'],
                        'instrument': {
                            'serial': row['instrument_serial'],
                            'description': row['instrument_description'],
                            'model': row['instrument_model'],
                        },
                        'counts': {
                            'measurements': int(row['measurement_count'] or 0),
                            'frames': int(row['frame_count'] or 0),
                            'audit_events': int(row['audit_count'] or 0),
                        },
                        'metadata': metadata or None,
                        'latest_measurement_at': last_measurement['measurement_timestamp'] if last_measurement else None,
                    }
                )
            return sessions
        finally:
            conn.close()

    def ensure_instrument(self, metadata: DeviceMetadata) -> int:
        conn = self.connect()
        return self._ensure_instrument(conn, metadata)

    def _ensure_instrument(self, conn: sqlite3.Connection, metadata: DeviceMetadata) -> int:
        serial = metadata.serial.strip() if metadata.serial else None
        description = metadata.description.strip() if metadata.description else None
        model = metadata.model.strip() if metadata.model else None
        if serial:
            row = conn.execute("SELECT id FROM instruments WHERE serial = ?", (serial,)).fetchone()
            if row:
                self._update_instrument(conn, row[0], description, model)
                return int(row[0])
        if description:
            row = conn.execute("SELECT id, serial FROM instruments WHERE description = ?", (description,)).fetchone()
            if row:
                if serial and row['serial'] != serial:
                    conn.execute(
                        "UPDATE instruments SET serial = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (serial, row['id']),
                    )
                self._update_instrument(conn, row['id'], description, model)
                return int(row['id'])
        with conn:
            cursor = conn.execute(
                "INSERT INTO instruments (serial, description, model) VALUES (?, ?, ?)",
                (serial, description, model),
            )
            return cursor.lastrowid

    def _update_instrument(
        self,
        conn: sqlite3.Connection,
        instrument_id: int,
        description: Optional[str],
        model: Optional[str],
    ) -> None:
        updates: Dict[str, Any] = {}
        if description:
            updates['description'] = description
        if model:
            updates['model'] = model
        if not updates:
            return
        assignments = ', '.join(f"{key} = ?" for key in updates)
        params = list(updates.values()) + [instrument_id]
        conn.execute(
            f"UPDATE instruments SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )

    def _ensure_retention_session(self, conn: sqlite3.Connection) -> int:
        row = conn.execute(
            "SELECT id FROM sessions WHERE note = ? LIMIT 1",
            ('Retention log',),
        ).fetchone()
        if row:
            return int(row['id']) if isinstance(row, sqlite3.Row) else int(row[0])

        metadata = DeviceMetadata(
            serial='SYSTEM-RETENTION',
            description='Retention log',
            model='system',
        )
        instrument_id = self._ensure_instrument(conn, metadata)
        cursor = conn.execute(
            "INSERT INTO sessions (instrument_id, started_at, note) VALUES (?, ?, ?)",
            (instrument_id, datetime.utcnow().isoformat(), 'Retention log'),
        )
        return int(cursor.lastrowid)


class SessionHandle:
    """Helper that records capture frames within a single acquisition session."""

    def __init__(self, database: Database, session_id: int, instrument_id: int, metadata: DeviceMetadata):
        self._database = database
        self.id = session_id
        self.instrument_id = instrument_id
        self.metadata = metadata
        self.session_metadata: Dict[str, Any] = {}
        self._closed = False
        self._frames = 0

    @property
    def frames(self) -> int:
        return self._frames

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        if not metadata:
            return
        self.session_metadata.update(metadata)
        self._database.set_session_metadata(self.id, metadata)

    def update_instrument(self, metadata: DeviceMetadata) -> int:
        self.metadata = metadata
        instrument_id = self._database.ensure_instrument(metadata)
        self._database.append_audit_event(
            self.id,
            AuditEvent(
                level='info',
                category='instrument',
                message='Updated instrument metadata',
                payload={
                    'serial': metadata.serial,
                    'description': metadata.description,
                    'model': metadata.model,
                },
            ),
        )
        return instrument_id

    def log_event(
        self,
        level: str,
        category: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit event for this session.
        
        Note: DEBUG level events are not saved to database to prevent spam.
        """
        # Filter out DEBUG logs - don't save to database
        if level.upper() != 'DEBUG':
            self._database.append_audit_event(self.id, AuditEvent(level, category, message, payload))

    def store_capture(
        self,
        captured_at: datetime,
        raw_frame: bytes,
        decoded: Dict[str, Any],
        derived_metrics: Optional[Dict[str, Any]] = None,
    ) -> StoredMeasurement:
        conn = self._database.connect()
        raw_hex = decoded.get('raw_hex') or raw_frame.hex()
        measurement = decoded.get('measurement', {})
        payload_json = json.dumps(decoded, ensure_ascii=False)
        measurement_timestamp = measurement.get('timestamp') or decoded.get('captured_at')
        value = measurement.get('value')
        unit = measurement.get('value_unit') or measurement.get('unit')
        temperature = measurement.get('temperature')
        temperature_unit = measurement.get('temperature_unit')
        with conn:
            # Always store raw frame (frame_id is NOT NULL in schema)
            cursor = conn.execute(
                "INSERT INTO raw_frames (session_id, captured_at, frame_hex, frame_bytes) VALUES (?, ?, ?, ?)",
                (self.id, captured_at.isoformat(), raw_hex, sqlite3.Binary(raw_frame)),
            )
            frame_id = cursor.lastrowid
            measurement_cursor = conn.execute(
                """
                INSERT INTO measurements (
                    session_id,
                    frame_id,
                    measurement_timestamp,
                    value,
                    unit,
                    temperature,
                    temperature_unit,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.id,
                    frame_id,
                    measurement_timestamp,
                    value,
                    unit,
                    temperature,
                    temperature_unit,
                    payload_json,
                ),
            )
            measurement_id = measurement_cursor.lastrowid
        if derived_metrics:
            self._database.set_derived_metrics(measurement_id, derived_metrics)
        self._frames += 1
        return StoredMeasurement(frame_id=frame_id, measurement_id=measurement_id)

    def close(self, ended_at: Optional[datetime] = None) -> None:
        if self._closed:
            return
        conn = self._database.connect()
        
        # Check measurement count before closing
        measurement_count = conn.execute(
            "SELECT COUNT(*) FROM measurements WHERE session_id = ?",
            (self.id,)
        ).fetchone()[0]
        
        # Delete session if it has fewer than 10 measurements
        if measurement_count < 10:
            with conn:
                # Delete related data first (foreign keys)
                conn.execute("DELETE FROM raw_frames WHERE session_id = ?", (self.id,))
                conn.execute("DELETE FROM measurements WHERE session_id = ?", (self.id,))
                conn.execute("DELETE FROM audit_events WHERE session_id = ?", (self.id,))
                conn.execute("DELETE FROM session_metadata WHERE session_id = ?", (self.id,))
                conn.execute("DELETE FROM sessions WHERE id = ?", (self.id,))
            self._closed = True
            return
        
        # Session has enough data - close it normally
        with conn:
            conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                ((ended_at or datetime.utcnow()).isoformat(), self.id),
            )
        self._closed = True

    def __enter__(self) -> "SessionHandle":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close(datetime.utcnow())


def _stringify(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float, str)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)

