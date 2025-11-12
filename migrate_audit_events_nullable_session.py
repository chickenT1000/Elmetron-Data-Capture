#!/usr/bin/env python3
"""
Migrate audit_events table to support system-wide logs.
Makes session_id nullable and adds source column.
"""

import sqlite3
from pathlib import Path

def migrate(db_path: str = None):
    if db_path is None:
        db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'
    else:
        db_path = Path(db_path)
    
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    
    # Check if audit_events table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'"
    )
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("audit_events table doesn't exist yet - will be created by database.py with new schema")
        conn.close()
        return
    
    # Check current schema
    cursor = conn.execute("PRAGMA table_info(audit_events)")
    columns = {row[1]: row for row in cursor.fetchall()}
    
    # Check if already migrated
    if 'source' in columns:
        print("[OK] Migration already applied - audit_events has 'source' column")
        conn.close()
        return
    
    print("Migrating audit_events table...")
    print(f"  Current columns: {list(columns.keys())}")
    
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Create new table with nullable session_id and source column
        conn.execute("""
            CREATE TABLE audit_events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'backend',
                
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
        """)
        print("  [OK] Created new table schema")
        
        # Copy existing data
        conn.execute("""
            INSERT INTO audit_events_new 
                (id, session_id, level, category, message, payload_json, created_at, source)
            SELECT 
                id, session_id, level, category, message, payload_json, created_at, 'backend'
            FROM audit_events
        """)
        rows_copied = conn.execute("SELECT COUNT(*) FROM audit_events_new").fetchone()[0]
        print(f"  [OK] Copied {rows_copied} existing rows")
        
        # Drop old table and rename
        conn.execute("DROP TABLE audit_events")
        conn.execute("ALTER TABLE audit_events_new RENAME TO audit_events")
        print("  [OK] Replaced old table")
        
        # Create indexes
        conn.execute("CREATE INDEX idx_audit_events_session ON audit_events(session_id)")
        conn.execute("CREATE INDEX idx_audit_events_created ON audit_events(created_at DESC)")
        conn.execute("CREATE INDEX idx_audit_events_level ON audit_events(level)")
        conn.execute("CREATE INDEX idx_audit_events_category ON audit_events(category)")
        conn.execute("CREATE INDEX idx_audit_events_source ON audit_events(source)")
        print("  [OK] Created indexes")
        
        conn.execute("COMMIT")
        print("\n[SUCCESS] Migration complete!")
        print("  - session_id is now nullable (supports system events)")
        print("  - Added source column (tracks backend/launcher/api)")
        print("  - Created performance indexes")
        
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    print("=== Audit Events Migration ===\n")
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(db_path)
