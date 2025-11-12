#!/usr/bin/env python3
"""Analyze audit events to understand filtering."""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'
conn = sqlite3.connect(str(db_path))

print("=== Audit Events Analysis ===\n")

# Total counts
cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
total = cursor.fetchone()[0]
print(f"Total events in database: {total:,}\n")

# By level
print("=== By Level ===")
cursor = conn.execute("""
    SELECT level, COUNT(*) as count 
    FROM audit_events 
    GROUP BY level 
    ORDER BY count DESC
""")
for level, count in cursor.fetchall():
    pct = (count / total * 100) if total > 0 else 0
    print(f"  {level:10s}: {count:>7,} ({pct:5.1f}%)")

# By category
print("\n=== By Category (Top 10) ===")
cursor = conn.execute("""
    SELECT category, COUNT(*) as count 
    FROM audit_events 
    GROUP BY category 
    ORDER BY count DESC
    LIMIT 10
""")
for cat, count in cursor.fetchall():
    pct = (count / total * 100) if total > 0 else 0
    print(f"  {cat:20s}: {count:>7,} ({pct:5.1f}%)")

# What UI sees (INFO and above, last 999)
print("\n=== What UI Sees (INFO and above, last 999) ===")
cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM audit_events 
    WHERE UPPER(level) != 'DEBUG'
    ORDER BY id DESC 
    LIMIT 999
""")
ui_count = cursor.fetchone()[0]
print(f"Events visible in UI: {ui_count:,}")

# Age analysis
print("\n=== Age Analysis ===")
now = datetime.utcnow()
cutoff_30 = (now - timedelta(days=30)).isoformat()
cutoff_60 = (now - timedelta(days=60)).isoformat()

cursor = conn.execute("""
    SELECT 
        COUNT(CASE WHEN created_at < ? THEN 1 END) as older_60,
        COUNT(CASE WHEN created_at >= ? AND created_at < ? THEN 1 END) as between_30_60,
        COUNT(CASE WHEN created_at >= ? THEN 1 END) as last_30,
        COUNT(CASE WHEN session_id IS NULL THEN 1 END) as system_events,
        COUNT(CASE WHEN session_id IS NOT NULL THEN 1 END) as session_events
    FROM audit_events
""", (cutoff_60, cutoff_60, cutoff_30, cutoff_30))
row = cursor.fetchone()
print(f"Older than 60 days:  {row[0]:>7,}")
print(f"30-60 days old:      {row[1]:>7,}")
print(f"Last 30 days:        {row[2]:>7,}")
print(f"\nSystem events:       {row[3]:>7,} (session_id IS NULL)")
print(f"Session events:      {row[4]:>7,} (tied to sessions)")

# Old system events that should be deleted
print("\n=== Old System Events (Should Be Deleted) ===")
cursor = conn.execute("""
    SELECT COUNT(*), MIN(created_at), MAX(created_at)
    FROM audit_events 
    WHERE session_id IS NULL 
    AND created_at < ?
""", (cutoff_30,))
row = cursor.fetchone()
print(f"System events older than 30 days: {row[0]:,}")
if row[0] > 0:
    print(f"  Oldest: {row[1]}")
    print(f"  Newest: {row[2]}")
    print("  ⚠️ These should have been deleted by retention policy!")

# Recent events sample
print("\n=== Recent Events Sample (Last 10) ===")
cursor = conn.execute("""
    SELECT level, category, message, session_id, created_at
    FROM audit_events 
    ORDER BY id DESC 
    LIMIT 10
""")
print(f"{'Level':<10} {'Category':<15} {'Session':<10} {'Message':<40}")
print("-" * 80)
for level, cat, msg, sess_id, created in cursor.fetchall():
    sess = str(sess_id) if sess_id else "SYSTEM"
    msg_short = msg[:37] + "..." if len(msg) > 40 else msg
    print(f"{level:<10} {cat:<15} {sess:<10} {msg_short:<40}")

conn.close()
