"""Durable capture journal with idempotent, conservative recovery."""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from .database import DeviceMetadata, SessionHandle

class SessionBuffer:
    def __init__(self, config, session_id: int, captures_dir: Path):
        self.session_id = session_id
        self.buffer_path = Path(captures_dir) / f'session_{session_id}_buffer.jsonl'
        self.measurement_count = 0
        self._file_handle = None

    @property
    def exists(self):
        return self.buffer_path.exists()

    def _write_line(self, record):
        if self._file_handle is None:
            raise RuntimeError('Journal is not open')
        self._file_handle.write(json.dumps(record, ensure_ascii=False) + '\n')

    def create(self, started_at, device_metadata, session_metadata=None):
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = self.buffer_path.open('x', encoding='utf-8')
        self._write_line({'type': 'session_start', 'version': 2, 'session_id': self.session_id,
                         'started_at': started_at.isoformat(), 'device': device_metadata,
                         'metadata': session_metadata or {}})
        self.flush()

    def append_measurement(self, captured_at, raw_frame: bytes, decoded, derived_metrics=None):
        decoded.setdefault('event_id', str(uuid4()))
        self._write_line({'type': 'measurement', 'event_id': decoded['event_id'],
                         'captured_at': captured_at.isoformat(), 'raw_frame_hex': raw_frame.hex(),
                         'decoded': decoded, 'derived_metrics': derived_metrics})
        self.measurement_count += 1

    def append_audit_event(self, level, category, message, payload=None):
        self._write_line({'type': 'audit_event', 'level': level, 'category': category,
                         'message': message, 'payload': payload})
        self.flush()

    def update_metadata(self, metadata):
        self._write_line({'type': 'metadata_update', 'metadata': metadata})
        self.flush()

    def flush(self):
        if self._file_handle:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())

    def close(self, ended_at=None, merge_to_db=True):
        if self._file_handle:
            if ended_at:
                self._write_line({'type': 'session_end', 'ended_at': ended_at.isoformat()})
            self.flush()
            self._file_handle.close()
            self._file_handle = None

    @staticmethod
    def is_buffer_orphaned(path):
        return Path(path).exists()

    @staticmethod
    def list_orphaned_buffers(captures_dir):
        return sorted(Path(captures_dir).glob('session_*_buffer.jsonl'))

    @staticmethod
    def _recover_single_buffer(buffer_path, database, delete_after_recovery):
        conn = database.connect()
        session = None
        recovered = 0
        ended_at = None
        with Path(buffer_path).open(encoding='utf-8-sig') as stream:
            for number,line in enumerate(stream,1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f'Incomplete journal line {number}; original retained') from exc
                kind = record.get('type')
                if kind == 'session_start':
                    row = conn.execute('SELECT instrument_id FROM sessions WHERE id=?', (record['session_id'],)).fetchone()
                    if not row:
                        raise ValueError('Journal session missing; manual recovery required')
                    device = record.get('device', {})
                    meta = DeviceMetadata(device.get('serial'), device.get('description'), device.get('model'))
                    session = SessionHandle(database, record['session_id'], row['instrument_id'], meta)
                elif kind == 'measurement' and session:
                    decoded = record['decoded']
                    event_id = record.get('event_id') or decoded.get('event_id')
                    if not event_id:
                        frame_id = decoded.get('storage', {}).get('frame_id')
                        row = conn.execute('SELECT frame_hex FROM raw_frames WHERE id=? AND session_id=?',
                                           (frame_id, session.id)).fetchone()
                        if row and row['frame_hex'] == record['raw_frame_hex']:
                            continue
                        raise ValueError('Legacy journal lacks stable identity; manual recovery required')
                    exists = conn.execute('SELECT 1 FROM measurements WHERE event_id=?', (event_id,)).fetchone()
                    session.store_capture(datetime.fromisoformat(record['captured_at'].replace('Z', '+00:00')),
                                          bytes.fromhex(record['raw_frame_hex']), decoded,
                                          record.get('derived_metrics'), event_id=event_id)
                    recovered += not bool(exists)
                elif kind == 'metadata_update' and session:
                    session.set_metadata(record['metadata'])
                elif kind == 'audit_event':
                    raise ValueError('Legacy audit journal requires manual recovery')
                elif kind == 'session_end':
                    ended_at = datetime.fromisoformat(record['ended_at'].replace('Z', '+00:00'))
        if not session:
            raise ValueError('Journal has no session header')
        session.close(ended_at or datetime.utcnow())
        if delete_after_recovery:
            Path(buffer_path).unlink()
        return {'session_id': session.id, 'measurements_recovered': recovered}

    @staticmethod
    def recover_orphaned_buffers(captures_dir, database, delete_after_recovery=True):
        summary = {'recovered_sessions': 0, 'recovered_measurements': 0,
                   'failed_recoveries': 0, 'buffers': []}
        for path in SessionBuffer.list_orphaned_buffers(captures_dir):
            try:
                result = SessionBuffer._recover_single_buffer(path, database, delete_after_recovery)
                summary['recovered_sessions'] += 1
                summary['recovered_measurements'] += result['measurements_recovered']
                summary['buffers'].append({'path': str(path), 'status': 'recovered', **result})
            except Exception as exc:
                summary['failed_recoveries'] += 1
                summary['buffers'].append({'path': str(path), 'status': 'retained', 'error': str(exc)})
        return summary
