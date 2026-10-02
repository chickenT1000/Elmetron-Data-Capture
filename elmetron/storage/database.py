"""SQLite persistence layer for Elmetron capture sessions."""
from __future__ import annotations

import json
import sqlite3
import threading
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
        self._local = threading.local()
        self._connection = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def _connection(self):
        return getattr(self._local, 'connection', None)

    @_connection.setter
    def _connection(self, value):
        self._local.connection = value

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(str(self._path), timeout=10)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA busy_timeout=10000")
            self._connection.execute("PRAGMA synchronous=FULL")
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def initialise(self) -> None:
        conn = self.connect()
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version > 2:
            raise RuntimeError('Database is newer than this application; refusing to downgrade.')
        if version < 2 and self._path.exists() and conn.execute("SELECT 1 FROM sqlite_master WHERE name='sessions'").fetchone():
            backup = self._path.with_name(self._path.name + '.pre-v2.bak')
            if not backup.exists():
                with sqlite3.connect(str(backup)) as destination:
                    conn.backup(destination)
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

    def start_session(
        self,
        started_at: datetime,
        metadata: DeviceMetadata,
        session_metadata: Optional[Dict[str, Any]] = None,
        operator_name: Optional[str] = None,
    ) -> "SessionHandle":
        conn = self.connect()
        instrument_id = self._ensure_instrument(conn, metadata)
        with conn:
            cursor = conn.execute(
                "INSERT INTO sessions (instrument_id, started_at, operator_name) VALUES (?, ?, ?)",
                (instrument_id, started_at.isoformat(), operator_name),
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


    def append_audit_event(self, session_id: Optional[int], event: AuditEvent, source: str = 'backend') -> Optional[int]:
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
            cursor = conn.execute(
                """
                INSERT INTO audit_events (session_id, level, category, message, payload_json, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, event.level, event.category, event.message, payload_json, source),
            )
        return cursor.lastrowid

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

        conn = sqlite3.connect(str(self._path), timeout=10)
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
        # Inspect columns as well as user_version: early installations used manual migrations.
        with conn:
            for table, column, declaration in [
                ('sessions', 'operator_name', 'TEXT'),
                ('audit_events', 'source', "TEXT DEFAULT 'backend'"),
                ('measurements', 'event_id', 'TEXT'),
            ]:
                columns = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
                if column not in columns:
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {declaration}')
            audit_columns = {row[1]: row for row in conn.execute('PRAGMA table_info(audit_events)')}
            audit_fk = list(conn.execute('PRAGMA foreign_key_list(audit_events)'))
            if audit_columns['session_id'][3] or not any(row[3] == 'session_id' and row[6] == 'SET NULL' for row in audit_fk):
                # Earliest databases required a session even for system events.
                # Rebuild transactionally, preserving identities and historical records.
                conn.execute("""CREATE TABLE audit_events_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NULL,
                    level TEXT NOT NULL, category TEXT NOT NULL, message TEXT NOT NULL,
                    payload_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'backend',
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL)""")
                conn.execute("""INSERT INTO audit_events_v2
                    (id,session_id,level,category,message,payload_json,created_at,source)
                    SELECT id,session_id,level,category,message,payload_json,created_at,source FROM audit_events""")
                conn.execute('DROP TABLE audit_events')
                conn.execute('ALTER TABLE audit_events_v2 RENAME TO audit_events')
                conn.execute('CREATE INDEX idx_audit_events_session ON audit_events(session_id)')
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_measurements_event ON measurements(event_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_measurements_session_timestamp ON measurements(session_id, measurement_timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_raw_frames_session_captured_at ON raw_frames(session_id, captured_at)')
            conn.execute('PRAGMA user_version = 2')

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

        conn = sqlite3.connect(str(self._path), timeout=10)
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
        event_id: Optional[str] = None,
    ) -> StoredMeasurement:
        conn = self._database.connect()
        event_id = event_id or decoded.get('event_id')
        raw_hex = decoded.get('raw_hex') or raw_frame.hex()
        measurement = decoded.get('measurement', {})
        payload_json = json.dumps(decoded, ensure_ascii=False)
        measurement_timestamp = measurement.get('timestamp') or decoded.get('captured_at')
        value = measurement.get('value')
        unit = measurement.get('value_unit') or measurement.get('unit')
        temperature = measurement.get('temperature')
        temperature_unit = measurement.get('temperature_unit')
        with conn:
            if event_id:
                existing = conn.execute('SELECT id, frame_id, session_id FROM measurements WHERE event_id=?', (event_id,)).fetchone()
                if existing:
                    if existing['session_id'] != self.id:
                        raise RuntimeError('Event identity belongs to a different session')
                    return StoredMeasurement(existing['frame_id'], existing['id'])
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
                    payload_json, event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    event_id,
                ),
            )
            measurement_id = measurement_cursor.lastrowid
            if derived_metrics:
                conn.execute('INSERT INTO derived_metrics (measurement_id, metrics_json) VALUES (?, ?)',
                             (measurement_id, json.dumps(derived_metrics, ensure_ascii=False)))
        self._frames += 1
        return StoredMeasurement(frame_id=frame_id, measurement_id=measurement_id)

    def close(self, ended_at: Optional[datetime] = None) -> None:
        if self._closed:
            return
        conn = self._database.connect()

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
