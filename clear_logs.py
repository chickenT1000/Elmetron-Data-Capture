#!/usr/bin/env python3
"""Clear old audit event logs from the database."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / 'measurements.db'

print(f"Opening database: {db_path}")
conn = sqlite3.connect(str(db_path))

# Check if audit_events table exists
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'")
table_exists = cursor.fetchone() is not None

if not table_exists:
    print("audit_events table does not exist yet.")
    print("Table will be created automatically when first log is written.")
    conn.close()
else:
    # Count existing events
    cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
    count = cursor.fetchone()[0]
    print(f"Found {count:,} audit events in database")
    
    if count > 0:
        # Delete all events
        print("Clearing all audit events...")
        conn.execute("DELETE FROM audit_events")
        conn.commit()
        print(f"SUCCESS: Deleted {count:,} old log events")
        print("Database is now clean!")
    else:
        print("Database is already clean - no events to delete.")
    
    conn.close()

print("\nRefresh the browser to see clean logs!")
