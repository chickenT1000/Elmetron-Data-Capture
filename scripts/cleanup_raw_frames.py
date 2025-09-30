"""Clean up existing raw frames from database to reclaim space.

This script removes all raw binary frames from the database while preserving
all measurements and derived metrics. Useful for reclaiming disk space on
older databases that were created before raw frame storage was disabled.

Usage:
    python scripts/cleanup_raw_frames.py

The script will:
1. Count and delete all rows from the raw_frames table
2. Run VACUUM to reclaim disk space
3. Report space savings

Note: Measurements are preserved, only raw binary frames are removed.
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

db_path = Path("data/elmetron.sqlite")

if not db_path.exists():
    print(f"[SKIP] Database not found: {db_path}")
    sys.exit(0)

# Get size before
size_before = db_path.stat().st_size / 1024 / 1024

print("=" * 60)
print("Cleaning up raw frames from database")
print("=" * 60)
print(f"Database: {db_path}")
print(f"Size before: {size_before:.2f} MB")
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check how many raw frames exist
cursor.execute("SELECT COUNT(*) FROM raw_frames")
frame_count = cursor.fetchone()[0]
print(f"Raw frames to delete: {frame_count:,}")

if frame_count == 0:
    print("[SKIP] No raw frames to delete")
    conn.close()
    sys.exit(0)

# Confirm action
response = input("\nProceed with deletion? [y/N]: ")
if response.lower() != 'y':
    print("Cancelled")
    conn.close()
    sys.exit(0)

# Delete all raw frames
print("\nDeleting raw frames...")
cursor.execute("DELETE FROM raw_frames")
deleted = cursor.rowcount
conn.commit()

print(f"[OK] Deleted {deleted:,} raw frames")

# Run VACUUM to reclaim space
print()
print("Running VACUUM to reclaim disk space...")
print("(This may take a moment...)")
conn.execute("VACUUM")
conn.close()

# Get size after
size_after = db_path.stat().st_size / 1024 / 1024
savings = size_before - size_after
savings_pct = (savings / size_before * 100) if size_before > 0 else 0

print("[OK] VACUUM complete")
print()
print("=" * 60)
print("Cleanup complete!")
print("=" * 60)
print(f"Size before: {size_before:.2f} MB")
print(f"Size after:  {size_after:.2f} MB")
print(f"Space saved: {savings:.2f} MB ({savings_pct:.1f}%)")
print()
print("Note: Measurements are preserved, only raw binary frames removed")
