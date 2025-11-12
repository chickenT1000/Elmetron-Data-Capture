#!/usr/bin/env python3
"""Manually run retention policy to clean up old data."""

import sys
from pathlib import Path
from datetime import datetime

# Add elmetron to path
sys.path.insert(0, str(Path(__file__).parent))

from elmetron.config import StorageConfig
from elmetron.storage.database import Database

print("=== Manual Retention Policy Run ===\n")

# Load config
db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'
config = StorageConfig(
    database_path=db_path,
    retention_days=30  # Use 30 days
)

print(f"Database: {db_path}")
print(f"Retention: {config.retention_days} days\n")

# Create database instance
database = Database(config)

# Backup first
import shutil
backup_path = db_path.parent / (db_path.stem + '_before_retention' + db_path.suffix + '.backup')
shutil.copy2(db_path, backup_path)
print(f"[OK] Backed up to: {backup_path.name}\n")

# Check what will be deleted
import sqlite3
from datetime import timedelta
conn = sqlite3.connect(str(db_path))
now = datetime.utcnow()
cutoff = (now - timedelta(days=30)).isoformat()

cursor = conn.execute("SELECT COUNT(*) FROM sessions WHERE started_at < ?", (cutoff,))
old_sessions = cursor.fetchone()[0]

cursor = conn.execute("""
    SELECT COUNT(*) FROM audit_events 
    WHERE session_id IS NULL AND created_at < ?
""", (cutoff,))
old_system_logs = cursor.fetchone()[0]

conn.close()

print(f"Sessions older than 30 days:      {old_sessions:,}")
print(f"System logs older than 30 days:   {old_system_logs:,}")
print(f"\nNote: Session events are deleted when sessions are deleted (CASCADE)")

if old_sessions == 0 and old_system_logs == 0:
    print("\nNothing to delete - database already clean!")
else:
    response = input(f"\nContinue and delete {old_sessions} sessions? (yes/no): ")
    
    if response.lower() == 'yes':
        print("\nRunning retention policy...")
        database.apply_retention(now)
        print("[OK] Retention policy executed!")
        
        # Verify results
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM sessions")
        remaining_sessions = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
        remaining_events = cursor.fetchone()[0]
        conn.close()
        
        print(f"\nResults:")
        print(f"  Remaining sessions:      {remaining_sessions:,}")
        print(f"  Remaining audit events:  {remaining_events:,}")
        
        print(f"\n[SUCCESS] Retention complete!")
        print(f"Backup: {backup_path}")
    else:
        print("Cancelled - no changes made")
