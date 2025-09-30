"""Quick database integrity check after Reset."""
import sqlite3
import sys
from pathlib import Path

db_path = Path("captures/device_data.db")

if not db_path.exists():
    print("❌ Database file not found")
    sys.exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Run SQLite integrity check
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    
    if result == "ok":
        print("✅ Database integrity: OK")
        
        # Quick stats
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM measurements")
        measurement_count = cursor.fetchone()[0]
        
        print(f"   Sessions: {session_count}")
        print(f"   Measurements: {measurement_count}")
        print("")
        print("✅ No corruption detected - graceful shutdown worked!")
    else:
        print(f"❌ Database integrity check failed: {result}")
        sys.exit(1)
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error checking database: {e}")
    sys.exit(1)
