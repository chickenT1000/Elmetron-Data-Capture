"""
Elmetron Data API Service

Standalone REST API server that provides access to captured session data.
This service runs INDEPENDENTLY of the device capture service, allowing
UI access to archived data even when the CX505 device is not connected.

Architecture:
    - Always-on HTTP API (port 8050)
    - Database-only operations (no device dependency)
    - Provides session history, measurements, and metadata
    - Reports live capture status from separate capture service

API Endpoints:
    GET  /health                              - Service health check
    GET  /api/sessions                        - List recent sessions
    GET  /api/sessions/:id                    - Get session details
    GET  /api/sessions/:id/measurements       - Get measurements for session
    GET  /api/sessions/:id/export            - Export session data (CSV/JSON)
    GET  /api/live/status                     - Check if live capture is running
    GET  /api/instruments                     - List known instruments
    GET  /api/stats                           - Database statistics
"""

from __future__ import annotations

import json
import sqlite3
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from elmetron.config import load_config
from elmetron.storage.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "captures" / "data_api_service.log")
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for browser access

# Global database instance
db: Optional[Database] = None
config = None

# Status file for live capture service communication
LIVE_STATUS_FILE = ROOT / "captures" / ".live_capture_status.json"

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Service health check - always returns OK if service is running."""
    return jsonify({
        'status': 'ok',
        'service': 'data_api',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'database': {
            'path': str(db.path) if db else None,
            'connected': db is not None,
        }
    })


@app.route('/api/live/status', methods=['GET'])
def live_status():
    """
    Check if live capture service is running by polling its health endpoint.
    
    Returns:
        {
            "live_capture_active": true/false,
            "device_connected": true/false,
            "current_session_id": 123 or null,
            "instrument": {"model": "CX-505", "serial": "00308/25"} or null,
            "last_update": "2025-09-30T12:34:56Z"
        }
    """
    import urllib.request
    import urllib.error
    
    # Get current session and instrument info from database
    session_id = None
    instrument_info = None
    try:
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # Get most recent active session
        session_row = conn.execute("""
            SELECT s.id, i.serial, i.model, i.description
            FROM sessions s
            LEFT JOIN instruments i ON s.instrument_id = i.id
            WHERE s.ended_at IS NULL
            ORDER BY s.started_at DESC
            LIMIT 1
        """).fetchone()
        
        if session_row:
            session_id = session_row['id']
            if session_row['serial']:
                instrument_info = {
                    'model': session_row['model'],
                    'serial': session_row['serial'],
                    'description': session_row['description']
                }
        
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching session info: {e}")
    
    # Try to poll the capture service health endpoint (port 8051)
    try:
        with urllib.request.urlopen('http://127.0.0.1:8051/health', timeout=2) as response:
            capture_health = json.loads(response.read().decode('utf-8'))
            
            # Capture service is running
            is_running = capture_health.get('state') == 'running'
            has_frames = capture_health.get('frames', 0) > 0
            last_frame = capture_health.get('last_frame_at')
            
            # Device is connected if service is actively capturing
            device_connected = is_running and has_frames
            
            return jsonify({
                'live_capture_active': device_connected,
                'device_connected': device_connected,
                'current_session_id': session_id,
                'instrument': instrument_info,
                'last_update': last_frame,
                'mode': 'live' if device_connected else 'archive',
                'frames_captured': capture_health.get('frames', 0)
            })
    
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError) as e:
        # Capture service is not reachable - fallback to archive mode
        logger.debug(f"Capture service not reachable: {e}")
        return jsonify({
            'live_capture_active': False,
            'device_connected': False,
            'current_session_id': None,
            'last_update': None,
            'mode': 'archive'
        })
    
    except Exception as e:
        logger.error(f"Error checking capture service health: {e}")
        return jsonify({
            'live_capture_active': False,
            'device_connected': False,
            'current_session_id': None,
            'last_update': None,
            'mode': 'archive',
            'error': str(e)
        }), 500


# ============================================================================
# Session Endpoints
# ============================================================================

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """
    Get list of sessions with filtering and sorting.
    
    Query params:
        limit: Number of sessions to return (default: 20, max: 100)
        operator: Filter by operator name (partial match)
        start_date: Filter sessions started after this date (ISO format)
        end_date: Filter sessions started before this date (ISO format)
        has_ph: Filter sessions with pH measurements (true/false)
        has_redox: Filter sessions with redox measurements (true/false)
        has_conductivity: Filter sessions with conductivity measurements (true/false)
        sort_by: Sort by field (started_at, measurement_count, duration) default: started_at
        order: Sort order (asc, desc) default: desc
    
    Returns: List of sessions with counts per parameter type
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        operator = request.args.get('operator', type=str)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        has_ph = request.args.get('has_ph', 'false', type=str).lower() == 'true'
        has_redox = request.args.get('has_redox', 'false', type=str).lower() == 'true'
        has_conductivity = request.args.get('has_conductivity', 'false', type=str).lower() == 'true'
        sort_by = request.args.get('sort_by', 'started_at', type=str)
        order = request.args.get('order', 'desc', type=str).lower()
        
        limit = max(1, min(limit, 100))
        
        # Build query with filters
        query_parts = []
        params = []
        
        # Base query with measurement counts per type
        query_parts.append("""
            SELECT
                s.id,
                s.started_at,
                s.ended_at,
                s.note,
                s.operator_name,
                i.serial AS instrument_serial,
                i.description AS instrument_description,
                i.model AS instrument_model,
                (SELECT COUNT(*) FROM measurements m WHERE m.session_id = s.id) AS measurement_count,
                (SELECT COUNT(*) FROM measurements m WHERE m.session_id = s.id AND m.unit LIKE '%pH%') AS ph_count,
                (SELECT COUNT(*) FROM measurements m WHERE m.session_id = s.id AND (m.unit LIKE '%mV%' OR m.unit LIKE '%ORP%')) AS redox_count,
                (SELECT COUNT(*) FROM measurements m WHERE m.session_id = s.id AND (m.unit LIKE '%S/cm%' OR m.unit LIKE '%siemens%')) AS conductivity_count,
                (SELECT COUNT(*) FROM raw_frames f WHERE f.session_id = s.id) AS frame_count,
                (SELECT COUNT(*) FROM audit_events a WHERE a.session_id = s.id) AS audit_count,
                (SELECT measurement_timestamp FROM measurements m WHERE m.session_id = s.id ORDER BY m.id DESC LIMIT 1) AS latest_measurement
            FROM sessions s
            LEFT JOIN instruments i ON s.instrument_id = i.id
        """)
        
        # Build WHERE clause
        where_conditions = []
        
        if operator:
            where_conditions.append('s.operator_name LIKE ?')
            params.append(f'%{operator}%')
        
        if start_date:
            where_conditions.append('s.started_at >= ?')
            params.append(start_date)
        
        if end_date:
            where_conditions.append('s.started_at <= ?')
            params.append(end_date)
        
        if where_conditions:
            query_parts.append('WHERE ' + ' AND '.join(where_conditions))
        
        # Add ORDER BY
        order_clause = 'ASC' if order == 'asc' else 'DESC'
        if sort_by == 'measurement_count':
            query_parts.append(f'ORDER BY measurement_count {order_clause}, s.id DESC')
        elif sort_by == 'duration':
            query_parts.append(f'ORDER BY (julianday(COALESCE(s.ended_at, datetime(\'now\'))) - julianday(s.started_at)) {order_clause}, s.id DESC')
        else:  # started_at
            query_parts.append(f'ORDER BY s.started_at {order_clause}, s.id DESC')
        
        query_parts.append('LIMIT ?')
        params.append(limit)
        
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(' '.join(query_parts), params).fetchall()
            sessions = []
            
            for row in rows:
                ph_count = int(row['ph_count'] or 0)
                redox_count = int(row['redox_count'] or 0)
                conductivity_count = int(row['conductivity_count'] or 0)
                
                # Apply parameter type filters
                if has_ph and ph_count == 0:
                    continue
                if has_redox and redox_count == 0:
                    continue
                if has_conductivity and conductivity_count == 0:
                    continue
                
                # Determine dominant parameter
                dominant = 'none'
                max_count = max(ph_count, redox_count, conductivity_count)
                if max_count > 0:
                    if ph_count == max_count:
                        dominant = 'ph'
                    elif redox_count == max_count:
                        dominant = 'redox'
                    elif conductivity_count == max_count:
                        dominant = 'conductivity'
                
                sessions.append({
                    'id': row['id'],
                    'started_at': row['started_at'],
                    'ended_at': row['ended_at'],
                    'note': row['note'],
                    'operator_name': row['operator_name'],
                    'instrument': {
                        'serial': row['instrument_serial'],
                        'description': row['instrument_description'],
                        'model': row['instrument_model'],
                    },
                    'counts': {
                        'measurements': int(row['measurement_count'] or 0),
                        'ph_measurements': ph_count,
                        'redox_measurements': redox_count,
                        'conductivity_measurements': conductivity_count,
                        'frames': int(row['frame_count'] or 0),
                        'audit_events': int(row['audit_count'] or 0),
                    },
                    'dominant_parameter': dominant,
                    'latest_measurement_at': row['latest_measurement'],
                })
            
            return jsonify({
                'sessions': sessions,
                'total': len(sessions)
            })
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session_details(session_id: int):
    """
    Get detailed information about a specific session.
    
    Returns:
        {
            "id": 1,
            "started_at": "2025-09-30T10:00:00Z",
            "ended_at": "2025-09-30T11:00:00Z",
            "note": "Test session",
            "instrument": {...},
            "counts": {...},
            "metadata": {...}
        }
    """
    try:
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        session_row = conn.execute(
            """
            SELECT 
                s.id,
                s.started_at,
                s.ended_at,
                s.note,
                i.serial AS instrument_serial,
                i.description AS instrument_description,
                i.model AS instrument_model
            FROM sessions s
            LEFT JOIN instruments i ON s.instrument_id = i.id
            WHERE s.id = ?
            """,
            (session_id,)
        ).fetchone()
        
        if not session_row:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get counts
        counts = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM measurements WHERE session_id = ?) AS measurements,
                (SELECT COUNT(*) FROM raw_frames WHERE session_id = ?) AS frames,
                (SELECT COUNT(*) FROM audit_events WHERE session_id = ?) AS audit_events
            """,
            (session_id, session_id, session_id)
        ).fetchone()
        
        # Get metadata
        metadata_rows = conn.execute(
            "SELECT key, value FROM session_metadata WHERE session_id = ?",
            (session_id,)
        ).fetchall()
        metadata = {row['key']: row['value'] for row in metadata_rows}
        
        # Get latest measurement timestamp
        latest = conn.execute(
            """
            SELECT measurement_timestamp 
            FROM measurements 
            WHERE session_id = ? 
            ORDER BY id DESC 
            LIMIT 1
            """,
            (session_id,)
        ).fetchone()
        
        conn.close()
        
        return jsonify({
            'id': session_row['id'],
            'started_at': session_row['started_at'],
            'ended_at': session_row['ended_at'],
            'note': session_row['note'],
            'instrument': {
                'serial': session_row['instrument_serial'],
                'description': session_row['instrument_description'],
                'model': session_row['instrument_model']
            },
            'counts': {
                'measurements': int(counts['measurements'] or 0),
                'frames': int(counts['frames'] or 0),
                'audit_events': int(counts['audit_events'] or 0)
            },
            'metadata': metadata or None,
            'latest_measurement_at': latest['measurement_timestamp'] if latest else None
        })
    
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id: int):
    """
    Permanently delete a session and all associated data.
    
    WARNING: This operation cannot be undone!
    
    Deletes:
    - Session record
    - All measurements
    - All raw frames
    - All audit events
    - Session metadata
    
    Returns:
        204 No Content on success
        404 if session not found
    """
    try:
        conn = sqlite3.connect(str(db.path))
        cursor = conn.cursor()
        
        # Check if session exists
        cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Get counts for logging
        cursor.execute("SELECT COUNT(*) FROM measurements WHERE session_id = ?", (session_id,))
        measurement_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM raw_frames WHERE session_id = ?", (session_id,))
        frame_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM audit_events WHERE session_id = ?", (session_id,))
        audit_count = cursor.fetchone()[0]
        
        logger.info(f"Deleting session {session_id}: {measurement_count} measurements, {frame_count} frames, {audit_count} audit events")
        
        # Delete in transaction (cascade delete)
        try:
            # Delete measurements
            cursor.execute("DELETE FROM measurements WHERE session_id = ?", (session_id,))
            
            # Delete raw frames
            cursor.execute("DELETE FROM raw_frames WHERE session_id = ?", (session_id,))
            
            # Delete audit events
            cursor.execute("DELETE FROM audit_events WHERE session_id = ?", (session_id,))
            
            # Delete session metadata
            cursor.execute("DELETE FROM session_metadata WHERE session_id = ?", (session_id,))
            
            # Delete session
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            
            conn.commit()
            
            logger.info(f"Successfully deleted session {session_id}")
            
            return '', 204  # No content
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
            return jsonify({'error': f'Failed to delete session: {str(e)}'}), 500
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/markers', methods=['GET'])
def get_session_markers(session_id: int):
    """
    Get all manual markers for a session.
    
    Returns markers as audit_events with event_type='manual_marker',
    sorted by timestamp with sequential numbering.
    """
    try:
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # Check if session exists
        session = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            conn.close()
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Get markers ordered by timestamp
        markers = conn.execute("""
            SELECT 
                id,
                session_id,
                event_timestamp,
                message,
                payload_json,
                created_at
            FROM audit_events
            WHERE session_id = ? AND event_type = 'manual_marker'
            ORDER BY event_timestamp ASC
        """, (session_id,)).fetchall()
        
        conn.close()
        
        # Build response with marker numbers
        result = []
        for idx, marker in enumerate(markers, start=1):
            payload = json.loads(marker['payload_json']) if marker['payload_json'] else {}
            result.append({
                'id': marker['id'],
                'session_id': marker['session_id'],
                'marker_number': idx,
                'event_timestamp': marker['event_timestamp'],
                'offset_seconds': payload.get('offset_seconds'),
                'note': payload.get('note'),
                'created_at': marker['created_at']
            })
        
        return jsonify({'markers': result})
    
    except Exception as e:
        logger.error(f"Error fetching markers for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/markers', methods=['POST'])
def create_session_marker(session_id: int):
    """
    Create a new manual marker for a session.
    
    Request body:
        {
            "event_timestamp": "2025-10-29T12:34:56Z",
            "offset_seconds": 123.45,
            "note": "Optional note"
        }
    
    Returns created marker with auto-calculated marker_number.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
        
        event_timestamp = data.get('event_timestamp')
        offset_seconds = data.get('offset_seconds')
        note = data.get('note', '')
        
        if not event_timestamp:
            return jsonify({'error': 'Missing event_timestamp'}), 400
        
        if offset_seconds is None:
            return jsonify({'error': 'Missing offset_seconds'}), 400
        
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # Check if session exists
        session = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            conn.close()
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Count existing markers (limit to 99)
        marker_count = conn.execute("""
            SELECT COUNT(*) as count 
            FROM audit_events 
            WHERE session_id = ? AND event_type = 'manual_marker'
        """, (session_id,)).fetchone()['count']
        
        if marker_count >= 99:
            conn.close()
            return jsonify({'error': 'Maximum 99 markers per session'}), 400
        
        # Create payload
        payload = {
            'offset_seconds': offset_seconds,
            'note': note
        }
        
        # Insert marker
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_events 
            (session_id, level, category, message, event_type, event_timestamp, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            'info',
            'marker',
            f'Manual marker added',
            'manual_marker',
            event_timestamp,
            json.dumps(payload)
        ))
        
        marker_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Created marker {marker_id} for session {session_id} at offset {offset_seconds}s")
        
        return jsonify({
            'id': marker_id,
            'session_id': session_id,
            'marker_number': marker_count + 1,
            'event_timestamp': event_timestamp,
            'offset_seconds': offset_seconds,
            'note': note,
            'created_at': datetime.now().isoformat()
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating marker for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/markers/<int:marker_id>', methods=['DELETE'])
def delete_session_marker(session_id: int, marker_id: int):
    """
    Delete a manual marker.
    
    Note: After deletion, remaining markers are automatically renumbered
    based on their timestamp order when retrieved via GET.
    """
    try:
        conn = sqlite3.connect(str(db.path))
        
        # Verify marker exists and belongs to session
        marker = conn.execute("""
            SELECT id FROM audit_events
            WHERE id = ? AND session_id = ? AND event_type = 'manual_marker'
        """, (marker_id, session_id)).fetchone()
        
        if not marker:
            conn.close()
            return jsonify({'error': 'Marker not found'}), 404
        
        # Delete marker
        conn.execute("DELETE FROM audit_events WHERE id = ?", (marker_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted marker {marker_id} from session {session_id}")
        
        return '', 204
    
    except Exception as e:
        logger.error(f"Error deleting marker {marker_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/rename', methods=['PATCH'])
def rename_session(session_id: int):
    """
    Rename a session by updating its note field.
    
    Request body:
        {
            "name": "New session name"
        }
    
    Returns:
        {
            "id": 1,
            "name": "New session name",
            "updated_at": "2025-10-04T12:34:56Z"
        }
    """
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Missing "name" in request body'}), 400
        
        name = data['name']
        
        # Validation
        if not isinstance(name, str):
            return jsonify({'error': 'Name must be a string'}), 400
        
        # Sanitize and validate
        name = name.strip()
        if len(name) == 0:
            return jsonify({'error': 'Session name cannot be empty'}), 400
        
        if len(name) > 50:
            return jsonify({'error': 'Session name must be 50 characters or less'}), 400
        
        # Check if session exists and validate uniqueness
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        session_row = conn.execute(
            "SELECT id FROM sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        
        if not session_row:
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Check for duplicate names (case-insensitive, excluding current session)
        duplicate_row = conn.execute(
            "SELECT id FROM sessions WHERE LOWER(note) = LOWER(?) AND id != ?",
            (name, session_id)
        ).fetchone()
        
        if duplicate_row:
            conn.close()
            return jsonify({'error': 'A session with this name already exists'}), 400
        
        # Update the note field (which stores the session name)
        updated_at = datetime.utcnow().isoformat() + 'Z'
        conn.execute(
            "UPDATE sessions SET note = ? WHERE id = ?",
            (name, session_id)
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Session {session_id} renamed to: {name}")
        
        return jsonify({
            'id': session_id,
            'name': name,
            'updated_at': updated_at
        })
    
    except Exception as e:
        logger.error(f"Error renaming session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/operator', methods=['PATCH'])
def update_session_operator(session_id: int):
    """
    Update operator name for a session.
    
    Request body:
        {
            "operator_name": "John Doe"
        }
    
    Returns:
        {
            "id": 1,
            "operator_name": "John Doe",
            "updated_at": "2025-10-29T12:34:56Z"
        }
    """
    try:
        data = request.get_json()
        if not data or 'operator_name' not in data:
            return jsonify({'error': 'Missing "operator_name" in request body'}), 400
        
        operator_name = data['operator_name']
        
        # Validation
        if operator_name is not None and not isinstance(operator_name, str):
            return jsonify({'error': 'Operator name must be a string or null'}), 400
        
        # Sanitize
        if operator_name:
            operator_name = operator_name.strip()
            if len(operator_name) > 100:
                return jsonify({'error': 'Operator name must be 100 characters or less'}), 400
            if len(operator_name) == 0:
                operator_name = None
        else:
            operator_name = None
        
        # Update in database
        conn = sqlite3.connect(str(db.path))
        try:
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            if not cursor.fetchone():
                return jsonify({'error': f'Session {session_id} not found'}), 404
            
            # Update operator name
            cursor.execute(
                "UPDATE sessions SET operator_name = ? WHERE id = ?",
                (operator_name, session_id)
            )
            conn.commit()
            
            logger.info(f"Session {session_id} operator updated to: {operator_name}")
            
            return jsonify({
                'id': session_id,
                'operator_name': operator_name,
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            })
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error updating operator for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/measurements', methods=['GET'])
def get_session_measurements(session_id: int):
    """
    Get measurements for a specific session.
    
    Query params:
        limit: Number of measurements to return (default: 1000, max: 10000)
        offset: Number of measurements to skip (default: 0)
        order: 'asc' or 'desc' (default: 'asc')
    
    Returns:
        {
            "session_id": 1,
            "measurements": [
                {
                    "id": 1,
                    "timestamp": "2025-09-30T10:00:01Z",
                    "value": -83.5,
                    "unit": "mV",
                    "temperature": 25.3,
                    "temperature_unit": "C",
                    "payload": {...}
                },
                ...
            ],
            "total": 150,
            "limit": 1000,
            "offset": 0
        }
    """
    try:
        limit = request.args.get('limit', 1000, type=int)
        offset = request.args.get('offset', 0, type=int)
        order = request.args.get('order', 'asc', type=str).lower()
        
        limit = max(1, min(limit, 10000))
        offset = max(0, offset)
        order_clause = 'ASC' if order == 'asc' else 'DESC'
        
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # Get total count
        total_row = conn.execute(
            "SELECT COUNT(*) as total FROM measurements WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        total = int(total_row['total'])
        
        # Get measurements
        rows = conn.execute(
            f"""
            SELECT 
                id,
                measurement_timestamp,
                value,
                unit,
                temperature,
                temperature_unit,
                payload_json
            FROM measurements
            WHERE session_id = ?
            ORDER BY id {order_clause}
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset)
        ).fetchall()
        
        conn.close()
        
        measurements = []
        for row in rows:
            payload = json.loads(row['payload_json']) if row['payload_json'] else {}
            
            # Convert to unified format for filtering
            measurement = {
                'id': row['id'],
                'timestamp': row['measurement_timestamp'],
                'ph': None,
                'redox': None,
                'conductivity': None,
                'temperature': row['temperature'],
                'value': row['value'],
                'unit': row['unit'],
                'temperature_unit': row['temperature_unit'],
                'payload': payload
            }
            
            # Map value to correct metric
            if row['unit'] and row['value'] is not None:
                unit_lower = row['unit'].lower()
                if 'ph' in unit_lower:
                    measurement['ph'] = row['value']
                elif 'mv' in unit_lower or 'orp' in unit_lower:
                    measurement['redox'] = row['value']
                elif 'us' in unit_lower or 'ms' in unit_lower or 's/cm' in unit_lower:
                    measurement['conductivity'] = row['value']
            
            measurements.append(measurement)
        
        # Convert back to original format
        result_measurements = []
        for m in measurements:
            result_measurements.append({
                'id': m.get('id'),
                'timestamp': m['timestamp'],
                'value': m.get('value'),
                'unit': m.get('unit'),
                'temperature': m.get('temperature'),
                'temperature_unit': m.get('temperature_unit'),
                'payload': m.get('payload', {})
            })
        
        return jsonify({
            'session_id': session_id,
            'measurements': result_measurements,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        logger.error(f"Error fetching measurements for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/measurements/recent', methods=['GET'])
def get_recent_measurements():
    """
    Get recent measurements from the most recent session for rolling charts.
    
    Query params:
        minutes: Number of minutes of history to return (default: 10, max: 60)
        session_id: Specific session ID (optional, defaults to most recent)
    
    Returns:
        {
            "session_id": 1,
            "start_time": "2025-10-02T10:00:00Z",
            "end_time": "2025-10-02T10:10:00Z",
            "measurements": [
                {
                    "timestamp": "2025-10-02T10:00:01Z",
                    "ph": 7.12,
                    "redox": -110.5,
                    "conductivity": 1450.2,
                    "temperature": 22.5
                },
                ...
            ],
            "count": 150
        }
    """
    try:
        minutes = request.args.get('minutes', 10, type=int)
        session_id = request.args.get('session_id', type=int)
        
        minutes = max(1, min(minutes, 60))  # Clamp between 1-60 minutes
        
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # If no session_id provided, get the most recent active session
        if session_id is None:
            session_row = conn.execute("""
                SELECT id FROM sessions 
                WHERE ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            
            if not session_row:
                # No active session, get most recent closed session
                session_row = conn.execute("""
                    SELECT id FROM sessions 
                    ORDER BY started_at DESC
                    LIMIT 1
                """).fetchone()
            
            if not session_row:
                conn.close()
                return jsonify({
                    'session_id': None,
                    'measurements': [],
                    'count': 0,
                    'message': 'No sessions found'
                })
            
            session_id = session_row['id']
        
        # Get measurements from the last N minutes
        rows = conn.execute("""
            SELECT 
                datetime(created_at, 'localtime') as timestamp,
                value,
                unit,
                temperature,
                temperature_unit,
                payload_json
            FROM measurements
            WHERE session_id = ?
            AND created_at >= datetime('now', ? || ' minutes')
            AND value IS NOT NULL
            ORDER BY created_at ASC
        """, (session_id, -minutes)).fetchall()
        
        conn.close()
        
        # Extract measurement values 
        measurements = []
        for row in rows:
            try:
                # Measurements are stored in table columns: value, unit, temperature, temperature_unit
                # Use these directly to determine the metric type
                temperature = row['temperature']
                value = row['value']
                unit = row['unit']
                
                # Quality filter: Skip frames with zero/invalid temperature (device initialization)
                if temperature is not None and temperature <= 0:
                    logger.debug(f"Skipping measurement with invalid temperature: {temperature}")
                    continue
                
                measurement = {
                    'timestamp': row['timestamp'],
                    'ph': None,
                    'redox': None,
                    'conductivity': None,
                    'temperature': temperature
                }
                
                # Map the value to the correct metric based on unit with range validation
                if unit and value is not None:
                    unit_lower = unit.lower()
                    
                    # pH measurement (valid range: -2 to 16)
                    if 'ph' in unit_lower:
                        if -2 <= value <= 16:
                            measurement['ph'] = value
                        else:
                            logger.debug(f"Skipping invalid pH: {value}")
                            continue
                    
                    # Redox/ORP measurement (valid range: -2000 to +2000 mV)
                    # Filters out extreme spikes when switching from pH mode
                    elif 'mv' in unit_lower or 'orp' in unit_lower:
                        if -2000 <= value <= 2000:
                            measurement['redox'] = value
                        else:
                            logger.debug(f"Skipping invalid redox: {value} mV")
                            continue
                    
                    # Conductivity (valid range: 0 to 500,000 µS/cm)
                    elif 'us' in unit_lower or 'ms' in unit_lower or 's/cm' in unit_lower or 'siemens' in unit_lower:
                        if 0 <= value <= 500000:
                            measurement['conductivity'] = value
                        else:
                            logger.debug(f"Skipping invalid conductivity: {value}")
                            continue
                
                measurements.append(measurement)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse measurement payload: {e}")
                continue
        
        # Get time range
        start_time = measurements[0]['timestamp'] if measurements else None
        end_time = measurements[-1]['timestamp'] if measurements else None
        
        return jsonify({
            'session_id': session_id,
            'start_time': start_time,
            'end_time': end_time,
            'measurements': measurements,
            'count': len(measurements)
        })
    
    except Exception as e:
        logger.error(f"Error fetching recent measurements: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/evaluation', methods=['GET'])
def get_session_evaluation(session_id: int):
    """
    Get session evaluation with measurements formatted for charting.
    This is a compatibility endpoint for the UI.
    
    Query params:
        anchor: Time anchor point ('start', 'calibration', etc.) - currently ignored
        limit: Max measurements to return (default: 10000)
    
    Returns evaluation format expected by UI.
    """
    try:
        anchor = request.args.get('anchor', 'start', type=str)
        limit = request.args.get('limit', 10000, type=int)
        limit = max(1, min(limit, 10000))
        
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # Get session details
        session_row = conn.execute("""
            SELECT 
                s.id,
                s.started_at,
                s.ended_at,
                s.note,
                i.serial as instrument_serial,
                i.description as instrument_description,
                i.model as instrument_model
            FROM sessions s
            LEFT JOIN instruments i ON s.instrument_id = i.id
            WHERE s.id = ?
        """, (session_id,)).fetchone()
        
        if not session_row:
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Get counts
        counts = conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM measurements WHERE session_id = ?) as measurements,
                (SELECT COUNT(*) FROM raw_frames WHERE session_id = ?) as frames,
                (SELECT COUNT(*) FROM audit_events WHERE session_id = ?) as audit_events
        """, (session_id, session_id, session_id)).fetchone()
        
        # Get measurements
        measurement_rows = conn.execute("""
            SELECT 
                m.id as measurement_id,
                m.frame_id,
                m.measurement_timestamp as timestamp,
                m.created_at,
                m.value,
                m.unit,
                m.temperature,
                m.temperature_unit,
                m.payload_json
            FROM measurements m
            WHERE m.session_id = ?
            ORDER BY m.id ASC
            LIMIT ?
        """, (session_id, limit)).fetchall()
        
        # Get markers for anchor calculation (before closing connection)
        markers_rows = conn.execute("""
            SELECT event_timestamp 
            FROM audit_events
            WHERE session_id = ? AND event_type = 'manual_marker'
            ORDER BY event_timestamp ASC
        """, (session_id,)).fetchall()
        
        conn.close()
        
        # Build evaluation response
        session = {
            'id': session_row['id'],
            'started_at': session_row['started_at'],
            'ended_at': session_row['ended_at'],
            'note': session_row['note'],
            'instrument': {
                'serial': session_row['instrument_serial'],
                'description': session_row['instrument_description'],
                'model': session_row['instrument_model']
            } if session_row['instrument_serial'] else None,
            'counts': {
                'measurements': counts['measurements'],
                'frames': counts['frames'],
                'audit_events': counts['audit_events']
            }
        }
        
        # Determine anchor time based on anchor parameter
        anchor_time = session_row['started_at']  # Default: session start
        
        if anchor == 'first_marker' or anchor == 'last_marker':
            if markers_rows:
                if anchor == 'first_marker':
                    anchor_time = markers_rows[0]['event_timestamp']
                else:  # last_marker
                    anchor_time = markers_rows[-1]['event_timestamp']
            else:
                # Fallback: if no markers, use first/last measurement
                if measurement_rows:
                    if anchor == 'first_marker':
                        anchor_time = measurement_rows[0]['timestamp']
                    else:  # last_marker
                        anchor_time = measurement_rows[-1]['timestamp']
        
        # Convert measurements to series format
        series = []
        values = []
        temps = []
        
        for row in measurement_rows:
            payload = json.loads(row['payload_json']) if row['payload_json'] else {}
            
            # Calculate offset from anchor (simplified - assumes ISO timestamp)
            offset_seconds = None
            if row['timestamp'] and anchor_time:
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                    anchor_ts = datetime.fromisoformat(anchor_time.replace('Z', '+00:00'))
                    offset_seconds = (ts - anchor_ts).total_seconds()
                except:
                    pass
            
            point = {
                'measurement_id': row['measurement_id'],
                'frame_id': row['frame_id'],
                'timestamp': row['timestamp'],
                'captured_at': row['created_at'],
                'offset_seconds': offset_seconds,
                'value': row['value'],
                'unit': row['unit'],
                'temperature': row['temperature'],
                'temperature_unit': row['temperature_unit'],
                'payload': payload
            }
            series.append(point)
            
            if row['value'] is not None:
                values.append(row['value'])
            if row['temperature'] is not None:
                temps.append(row['temperature'])
        
        # Calculate statistics
        value_stats = {
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'average': sum(values) / len(values) if values else None,
            'samples': len(values),
            'unit': series[0]['unit'] if series else None
        }
        
        temp_stats = {
            'min': min(temps) if temps else None,
            'max': max(temps) if temps else None,
            'average': sum(temps) / len(temps) if temps else None,
            'samples': len(temps),
            'unit': series[0]['temperature_unit'] if series else None
        }
        
        # Calculate duration
        duration_seconds = None
        if session_row['ended_at'] and session_row['started_at']:
            try:
                from datetime import datetime
                end_ts = datetime.fromisoformat(session_row['ended_at'].replace('Z', '+00:00'))
                start_ts = datetime.fromisoformat(session_row['started_at'].replace('Z', '+00:00'))
                duration_seconds = (end_ts - start_ts).total_seconds()
            except:
                pass
        
        return jsonify({
            'session': session,
            'anchor': anchor,
            'anchor_timestamp': anchor_time,
            'series': series,
            'markers': [],  # TODO: Extract from audit events
            'statistics': {
                'value': value_stats,
                'temperature': temp_stats
            },
            'duration_seconds': duration_seconds,
            'samples': len(series)
        })
    
    except Exception as e:
        logger.error(f"Error generating evaluation for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<int:session_id>/export', methods=['GET'])
def export_session(session_id: int):
    """
    Export session data as CSV or JSON.
    
    Query params:
        format: 'csv' or 'json' (default: 'csv')
    
    Returns:
        CSV or JSON file download
    """
    try:
        format_type = request.args.get('format', 'csv', type=str).lower()
        
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        # Get session info
        session_row = conn.execute(
            "SELECT started_at, ended_at, note FROM sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        
        if not session_row:
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Get all measurements
        rows = conn.execute(
            """
            SELECT 
                measurement_timestamp,
                value,
                unit,
                temperature,
                temperature_unit
            FROM measurements
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        ).fetchall()
        
        conn.close()
        
        if format_type == 'json':
            data = {
                'session_id': session_id,
                'started_at': session_row['started_at'],
                'ended_at': session_row['ended_at'],
                'note': session_row['note'],
                'measurements': [
                    {
                        'timestamp': row['measurement_timestamp'],
                        'value': row['value'],
                        'unit': row['unit'],
                        'temperature': row['temperature'],
                        'temperature_unit': row['temperature_unit']
                    }
                    for row in rows
                ]
            }
            return Response(
                json.dumps(data, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename=session_{session_id}.json'}
            )
        
        else:  # CSV format
            csv_lines = ['Timestamp,Value,Unit,Temperature,Temperature Unit']
            for row in rows:
                csv_lines.append(
                    f"{row['measurement_timestamp']},"
                    f"{row['value'] or ''},"
                    f"{row['unit'] or ''},"
                    f"{row['temperature'] or ''},"
                    f"{row['temperature_unit'] or ''}"
                )
            
            csv_content = '\n'.join(csv_lines)
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=session_{session_id}.csv'}
            )
    
    except Exception as e:
        logger.error(f"Error exporting session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Instrument Endpoints
# ============================================================================

@app.route('/api/instruments', methods=['GET'])
def get_instruments():
    """
    Get list of all known instruments.
    
    Returns:
        {
            "instruments": [
                {
                    "id": 1,
                    "serial": "EL680921",
                    "description": "CX505 Lab Unit",
                    "model": "CX505",
                    "created_at": "2025-09-30T10:00:00Z"
                },
                ...
            ]
        }
    """
    try:
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT id, serial, description, model, created_at
            FROM instruments
            ORDER BY id DESC
            """
        ).fetchall()
        
        conn.close()
        
        instruments = [
            {
                'id': row['id'],
                'serial': row['serial'],
                'description': row['description'],
                'model': row['model'],
                'created_at': row['created_at']
            }
            for row in rows
        ]
        
        return jsonify({
            'instruments': instruments,
            'total': len(instruments)
        })
    
    except Exception as e:
        logger.error(f"Error fetching instruments: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Statistics Endpoints
# ============================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get database statistics.
    
    Returns:
        {
            "total_sessions": 10,
            "total_measurements": 1500,
            "total_instruments": 2,
            "database_size_mb": 5.2,
            "oldest_session": "2025-09-01T10:00:00Z",
            "newest_session": "2025-09-30T10:00:00Z"
        }
    """
    try:
        conn = sqlite3.connect(str(db.path))
        conn.row_factory = sqlite3.Row
        
        stats_row = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM sessions) AS total_sessions,
                (SELECT COUNT(*) FROM measurements) AS total_measurements,
                (SELECT COUNT(*) FROM instruments) AS total_instruments,
                (SELECT MIN(started_at) FROM sessions) AS oldest_session,
                (SELECT MAX(started_at) FROM sessions) AS newest_session
            """
        ).fetchone()
        
        conn.close()
        
        # Get database file size
        db_size_bytes = db.path.stat().st_size if db.path.exists() else 0
        db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
        
        return jsonify({
            'total_sessions': int(stats_row['total_sessions'] or 0),
            'total_measurements': int(stats_row['total_measurements'] or 0),
            'total_instruments': int(stats_row['total_instruments'] or 0),
            'database_size_mb': db_size_mb,
            'oldest_session': stats_row['oldest_session'],
            'newest_session': stats_row['newest_session']
        })
    
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Service Management
# ============================================================================

def initialize_database():
    """Initialize database connection and ensure schema exists."""
    global db, config
    
    try:
        # Load config from default path
        config_path = ROOT / "config" / "app.toml"
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            sys.exit(1)
            
        config = load_config(config_path)
        db = Database(config.storage)
        db.initialise()
        logger.info(f"[OK] Database initialized: {db.path}")
        logger.info(f"   Journal mode: WAL")
        logger.info(f"   Database size: {db.path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)


def cleanup():
    """Cleanup resources before shutdown."""
    global db
    
    logger.info("[SHUTDOWN] Shutting down Data API service...")
    
    if db:
        try:
            db.close()
            logger.info("[OK] Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
    
    logger.info("[BYE] Data API service stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    logger.info(f"[SIGNAL] Received signal {signal_name}")
    cleanup()
    sys.exit(0)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the Data API service."""
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("[START] Elmetron Data API Service Starting")
    logger.info("=" * 60)
    logger.info(f"   Root: {ROOT}")
    logger.info(f"   Port: 8050")
    logger.info(f"   Mode: Always-On (No Device Required)")
    logger.info("")
    
    # Initialize database
    initialize_database()
    
    logger.info("")
    logger.info("[API] API Endpoints Available:")
    logger.info("   GET  /health                              - Service health")
    logger.info("   GET  /api/live/status                     - Check live capture status")
    logger.info("   GET  /api/sessions                        - List sessions")
    logger.info("   GET  /api/sessions/:id                    - Session details")
    logger.info("   GET  /api/sessions/:id/measurements       - Session measurements")
    logger.info("   GET  /api/sessions/:id/export?format=csv  - Export data")
    logger.info("   GET  /api/instruments                     - List instruments")
    logger.info("   GET  /api/stats                           - Database statistics")
    logger.info("")
    logger.info("[OK] Data API Service Ready!")
    logger.info("=" * 60)
    
    try:
        # Run Flask app
        app.run(
            host='127.0.0.1',
            port=8050,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"[ERROR] Service error: {e}", exc_info=True)
        cleanup()
        sys.exit(1)


if __name__ == '__main__':
    main()
