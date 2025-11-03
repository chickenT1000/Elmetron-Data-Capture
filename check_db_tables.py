#!/usr/bin/env python3
"""Check database table sizes."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'
conn = sqlite3.connect(str(db_path))

print("=== Database Tables and Row Counts ===\n")

cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

total_rows = 0
for table in tables:
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        print(f"{table:30s}: {count:>10,} rows")
        total_rows += count
    except Exception as e:
        print(f"{table:30s}: ERROR - {e}")

print(f"\n{'TOTAL':30s}: {total_rows:>10,} rows")

# Specifically check audit_events
print("\n=== Audit Events Details ===")
cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN session_id IS NULL THEN 1 END) as system_events,
        COUNT(CASE WHEN session_id IS NOT NULL THEN 1 END) as session_events,
        MIN(created_at) as oldest,
        MAX(created_at) as newest
    FROM audit_events
""")
row = cursor.fetchone()
print(f"Total audit events:   {row[0]:>10,}")
print(f"System events:        {row[1]:>10,} (session_id IS NULL)")
print(f"Session events:       {row[2]:>10,} (tied to sessions)")
print(f"Oldest event:         {row[3]}")
print(f"Newest event:         {row[4]}")

conn.close()
