"""
Migration: Add marker fields to audit_events table
"""
import sqlite3
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def migrate():
    db_path = Path(__file__).parent / 'data' / 'elmetron.sqlite'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(audit_events)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Add event_type if not exists
        if 'event_type' not in columns:
            print("Adding event_type column...")
            cursor.execute("""
                ALTER TABLE audit_events 
                ADD COLUMN event_type TEXT DEFAULT 'audit'
            """)
            print("✓ Added event_type column")
        else:
            print("✓ event_type column already exists")
        
        # Add event_timestamp if not exists
        if 'event_timestamp' not in columns:
            print("Adding event_timestamp column...")
            cursor.execute("""
                ALTER TABLE audit_events 
                ADD COLUMN event_timestamp TEXT
            """)
            print("✓ Added event_timestamp column")
            
            # Backfill with created_at for existing records
            cursor.execute("""
                UPDATE audit_events 
                SET event_timestamp = created_at 
                WHERE event_timestamp IS NULL
            """)
            print("✓ Backfilled event_timestamp from created_at")
        else:
            print("✓ event_timestamp column already exists")
        
        # Add measurement_id if not exists (optional link to measurement)
        if 'measurement_id' not in columns:
            print("Adding measurement_id column...")
            cursor.execute("""
                ALTER TABLE audit_events 
                ADD COLUMN measurement_id INTEGER
            """)
            print("✓ Added measurement_id column")
        else:
            print("✓ measurement_id column already exists")
        
        # Create index for marker queries
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_events_type_session 
            ON audit_events(event_type, session_id, event_timestamp)
        """)
        print("✓ Created index idx_audit_events_type_session")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
