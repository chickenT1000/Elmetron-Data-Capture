#!/usr/bin/env python3
"""Clean up DEBUG logs from database."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'

print("=== Cleaning DEBUG Logs from Database ===\n")

# Backup first
backup_path = db_path.parent / (db_path.stem + '_before_debug_cleanup' + db_path.suffix + '.backup')
import shutil
shutil.copy2(db_path, backup_path)
print(f"[OK] Backed up database to: {backup_path.name}\n")

conn = sqlite3.connect(str(db_path))

# Count DEBUG logs
cursor = conn.execute("SELECT COUNT(*) FROM audit_events WHERE UPPER(level) = 'DEBUG'")
debug_count = cursor.fetchone()[0]
print(f"DEBUG logs to delete: {debug_count:,}")

if debug_count == 0:
    print("No DEBUG logs to delete - database already clean!")
    conn.close()
else:
    # Get breakdown by category
    print("\nDEBUG logs by category:")
    cursor = conn.execute("""
        SELECT category, COUNT(*) as count 
        FROM audit_events 
        WHERE UPPER(level) = 'DEBUG' 
        GROUP BY category 
        ORDER BY count DESC
    """)
    for cat, count in cursor.fetchall():
        print(f"  {cat:20s}: {count:>7,}")
    
    # Confirm deletion
    print(f"\n[WARNING] About to DELETE {debug_count:,} DEBUG logs from database")
    response = input("Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        print("\nDeleting DEBUG logs...")
        with conn:
            cursor = conn.execute("DELETE FROM audit_events WHERE UPPER(level) = 'DEBUG'")
            deleted = cursor.rowcount
        
        print(f"[OK] Deleted {deleted:,} DEBUG logs")
        
        # Show new stats
        cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
        remaining = cursor.fetchone()[0]
        print(f"[OK] Remaining audit events: {remaining:,}")
        
        # Vacuum to reclaim space
        print("\nReclaiming disk space...")
        conn.execute("VACUUM")
        print("[OK] Database optimized")
        
        conn.close()
        
        # Show file size reduction
        import os
        old_size = os.path.getsize(backup_path) / 1024 / 1024
        new_size = os.path.getsize(db_path) / 1024 / 1024
        saved = old_size - new_size
        print(f"\nDatabase size:")
        print(f"  Before: {old_size:.2f} MB")
        print(f"  After:  {new_size:.2f} MB")
        print(f"  Saved:  {saved:.2f} MB ({saved/old_size*100:.1f}%)")
        
        print("\n[SUCCESS] Cleanup complete!")
        print(f"\nBackup saved at: {backup_path}")
    else:
        print("Cancelled - no changes made")
        conn.close()
