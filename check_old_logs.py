#!/usr/bin/env python3
"""Check why old logs aren't being deleted."""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'
conn = sqlite3.connect(str(db_path))

print("=== Old Logs Investigation ===\n")

# Check retention configuration
retention_days = 90  # From config
now = datetime.utcnow()
cutoff_30 = (now - timedelta(days=30)).isoformat()
cutoff_60 = (now - timedelta(days=60)).isoformat()
cutoff_90 = (now - timedelta(days=retention_days)).isoformat()

print(f"Retention policy: {retention_days} days")
print(f"Cutoff date (30 days): {cutoff_30}")
print(f"Cutoff date (90 days): {cutoff_90}\n")

# Check old sessions
print("=== Old Sessions ===")
cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN started_at < ? THEN 1 END) as older_30,
        COUNT(CASE WHEN started_at < ? THEN 1 END) as older_60,
        COUNT(CASE WHEN started_at < ? THEN 1 END) as older_90,
        MIN(started_at) as oldest,
        MAX(started_at) as newest
    FROM sessions
""", (cutoff_30, cutoff_60, cutoff_90))
row = cursor.fetchone()
print(f"Total sessions:          {row[0]:,}")
print(f"Older than 30 days:      {row[1]:,}")
print(f"Older than 60 days:      {row[2]:,}")
print(f"Older than 90 days:      {row[3]:,} (should be deleted by retention!)")
print(f"Oldest session:          {row[4]}")
print(f"Newest session:          {row[5]}")

# Check audit events for those old sessions
print("\n=== Audit Events for Old Sessions ===")
cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN ae.created_at < ? THEN 1 END) as older_30,
        COUNT(CASE WHEN ae.created_at < ? THEN 1 END) as older_60,
        MIN(ae.created_at) as oldest,
        MAX(ae.created_at) as newest
    FROM audit_events ae
    WHERE ae.session_id IS NOT NULL
""", (cutoff_30, cutoff_60))
row = cursor.fetchone()
print(f"Total session events:    {row[0]:,}")
print(f"Older than 30 days:      {row[1]:,}")
print(f"Older than 60 days:      {row[2]:,}")
print(f"Oldest event:            {row[3]}")
print(f"Newest event:            {row[4]}")

# Check for orphaned events (session deleted but events remain)
print("\n=== Orphaned Events Check ===")
cursor = conn.execute("""
    SELECT COUNT(*)
    FROM audit_events ae
    LEFT JOIN sessions s ON ae.session_id = s.id
    WHERE ae.session_id IS NOT NULL
    AND s.id IS NULL
""")
orphaned = cursor.fetchone()[0]
print(f"Orphaned events (session deleted): {orphaned:,}")

if orphaned > 0:
    print("\n[WARNING] Found orphaned events - sessions were deleted but events remain!")
    print("This should not happen with proper CASCADE DELETE.")

# Check if retention has ever run
print("\n=== Retention History ===")
cursor = conn.execute("""
    SELECT COUNT(*), MAX(created_at)
    FROM audit_events
    WHERE category = 'retention'
""")
row = cursor.fetchone()
retention_runs = row[0]
last_run = row[1]
print(f"Retention events logged: {retention_runs}")
print(f"Last retention run:      {last_run or 'Never'}")

if retention_runs == 0:
    print("\n[WARNING] Retention policy has NEVER run!")
    print("This explains why old data hasn't been deleted.")

# Sample of old events
print("\n=== Sample Old Events (Oldest 5) ===")
cursor = conn.execute("""
    SELECT 
        ae.created_at,
        ae.level,
        ae.category,
        ae.message,
        ae.session_id,
        s.started_at as session_start
    FROM audit_events ae
    LEFT JOIN sessions s ON ae.session_id = s.id
    WHERE ae.session_id IS NOT NULL
    ORDER BY ae.created_at ASC
    LIMIT 5
""")
print(f"{'Event Date':<20} {'Level':<10} {'Category':<15} {'Sess ID':<8} {'Session Start'}")
print("-" * 80)
for row in cursor.fetchall():
    sess_id = str(row[4]) if row[4] else "NULL"
    sess_start = row[5] or "DELETED?"
    print(f"{row[0]:<20} {row[1]:<10} {row[2]:<15} {sess_id:<8} {sess_start}")

conn.close()

print("\n=== Recommendation ===")
if retention_runs == 0:
    print("Retention policy needs to run at service startup.")
    print("Check elmetron/storage/database.py initialise() method.")
elif orphaned > 0:
    print(f"Clean up {orphaned} orphaned events manually.")
else:
    print("Old sessions and their events should be deleted by retention policy.")
    print(f"Sessions older than {retention_days} days should be deleted.")
