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
            "last_update": "2025-09-30T12:34:56Z"
        }
    """
    import urllib.request
    import urllib.error
    
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
                'current_session_id': None,  # TODO: Get from latest session in DB
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
    Get list of recent sessions.
    
    Query params:
        limit: Number of sessions to return (default: 20, max: 100)
    
    Returns:
        {
            "sessions": [
                {
                    "id": 1,
                    "started_at": "2025-09-30T10:00:00Z",
                    "ended_at": "2025-09-30T11:00:00Z",
                    "note": "Test session",
                    "instrument": {...},
                    "counts": {
                        "measurements": 150,
                        "frames": 150,
                        "audit_events": 5
                    },
                    "metadata": {...},
                    "latest_measurement_at": "2025-09-30T10:59:59Z"
                },
                ...
            ],
            "total": 1
        }
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        limit = max(1, min(limit, 100))
        
        sessions = db.recent_sessions(limit=limit)
        
        return jsonify({
            'sessions': sessions,
            'total': len(sessions)
        })
    
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
                    "temperature_unit": "°C",
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
            measurements.append({
                'id': row['id'],
                'timestamp': row['measurement_timestamp'],
                'value': row['value'],
                'unit': row['unit'],
                'temperature': row['temperature'],
                'temperature_unit': row['temperature_unit'],
                'payload': payload
            })
        
        return jsonify({
            'session_id': session_id,
            'measurements': measurements,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        logger.error(f"Error fetching measurements for session {session_id}: {e}", exc_info=True)
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
        
        # Convert measurements to series format
        series = []
        values = []
        temps = []
        anchor_time = session_row['started_at']  # Use start as anchor
        
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
