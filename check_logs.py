#!/usr/bin/env python3
"""Check audit_events logs in database."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / 'measurements.db'
conn = sqlite3.connect(str(db_path))

print("=== AUDIT EVENTS STATISTICS ===\n")

# Total count and date range
cursor = conn.execute('''
    SELECT 
        COUNT(*) as total,
        MIN(created_at) as oldest,
        MAX(created_at) as newest
    FROM audit_events
''')
row = cursor.fetchone()
print(f"Total events: {row[0]:,}")
print(f"Oldest: {row[1]}")
print(f"Newest: {row[2]}")

# By level
print("\n=== BY LEVEL ===")
cursor = conn.execute('''
    SELECT level, COUNT(*) as count 
    FROM audit_events 
    GROUP BY level 
    ORDER BY count DESC
''')
for level, count in cursor.fetchall():
    print(f"  {level:10s}: {count:,} events")

# By category
print("\n=== BY CATEGORY ===")
cursor = conn.execute('''
    SELECT category, COUNT(*) as count 
    FROM audit_events 
    GROUP BY category 
    ORDER BY count DESC
    LIMIT 10
''')
for cat, count in cursor.fetchall():
    print(f"  {cat:15s}: {count:,} events")

# Recent 10
print("\n=== MOST RECENT 10 LOGS ===")
cursor = conn.execute('''
    SELECT id, level, category, message, created_at 
    FROM audit_events 
    ORDER BY id DESC 
    LIMIT 10
''')
print(f"{'ID':>6} | {'Level':8s} | {'Category':15s} | {'Message':40s} | {'Created At'}")
print("-" * 110)
for row in cursor.fetchall():
    msg = row[3][:40] if row[3] else ""
    print(f"{row[0]:6d} | {row[1]:8s} | {row[2]:15s} | {msg:40s} | {row[4]}")

conn.close()
