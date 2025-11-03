"""
Clean up sessions with fewer than 10 measurements.
"""
import sqlite3
from pathlib import Path

def cleanup_short_sessions(db_path: str = 'data/elmetron.sqlite', min_measurements: int = 10, auto_confirm: bool = False):
    """Remove sessions that have fewer than minimum measurements."""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Find sessions with too few measurements
        cursor = conn.execute("""
            SELECT s.id, s.started_at, COUNT(m.id) as measurement_count
            FROM sessions s
            LEFT JOIN measurements m ON s.id = m.session_id
            GROUP BY s.id
            HAVING measurement_count < ?
            ORDER BY s.started_at DESC
        """, (min_measurements,))
        
        sessions_to_delete = cursor.fetchall()
        
        if not sessions_to_delete:
            print(f"[OK] No sessions found with fewer than {min_measurements} measurements")
            return 0
        
        print(f"Found {len(sessions_to_delete)} session(s) with < {min_measurements} measurements:")
        for session in sessions_to_delete:
            print(f"  - Session {session['id']}: {session['measurement_count']} measurements (started: {session['started_at']})")
        
        # Confirm deletion
        if not auto_confirm:
            try:
                response = input(f"\nDelete these {len(sessions_to_delete)} session(s)? (yes/no): ")
                if response.lower() != 'yes':
                    print("Cancelled.")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return 0
        
        # Delete sessions and related data
        deleted_count = 0
        for session in sessions_to_delete:
            session_id = session['id']
            with conn:
                # Delete related data first (respects foreign keys)
                conn.execute("DELETE FROM raw_frames WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM measurements WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM audit_events WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM session_metadata WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            deleted_count += 1
            print(f"  [OK] Deleted session {session_id}")
        
        print(f"\n[OK] Successfully deleted {deleted_count} session(s)")
        
        # Vacuum to reclaim space
        print("Vacuuming database to reclaim space...")
        conn.execute("VACUUM")
        print("[OK] Database optimized")
        
        return deleted_count
        
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    
    # Allow custom minimum from command line
    min_measurements = 10
    auto_confirm = False
    
    for arg in sys.argv[1:]:
        if arg == '--yes' or arg == '-y':
            auto_confirm = True
        else:
            try:
                min_measurements = int(arg)
            except ValueError:
                print(f"Invalid argument: {arg}")
                print("Usage: python cleanup_short_sessions.py [MIN_MEASUREMENTS] [--yes|-y]")
                sys.exit(1)
    
    print(f"Cleaning up sessions with fewer than {min_measurements} measurements...\n")
    cleanup_short_sessions(min_measurements=min_measurements, auto_confirm=auto_confirm)
