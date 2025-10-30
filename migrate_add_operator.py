#!/usr/bin/env python3
"""
Database migration: Add operator_name column to sessions table
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path("data/elmetron.sqlite")
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'operator_name' in columns:
            print("[OK] operator_name column already exists")
            return True
        
        print("Adding operator_name column to sessions table...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN operator_name TEXT NULL")
        
        print("Creating index on operator_name...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_operator ON sessions(operator_name)")
        
        print("Creating index on started_at...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)")
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'operator_name' in columns:
            print("[OK] Migration successful!")
            print(f"[OK] Sessions table now has {len(columns)} columns")
            return True
        else:
            print("[FAIL] Migration failed - column not found after adding")
            return False
            
    except Exception as e:
        print(f"[FAIL] Migration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 70)
    print("DATABASE MIGRATION: Add operator_name to sessions")
    print("=" * 70)
    success = migrate()
    print("=" * 70)
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
    print("=" * 70)
