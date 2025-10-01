import sqlite3
from pathlib import Path

# Check both databases
for db_path in ['data/elmetron.sqlite', 'captures/device_data.db']:
    print(f'\n{"="*60}')
    print(f'Database: {db_path}')
    print(f'{"="*60}')
    
    if not Path(db_path).exists():
        print(f'  File does not exist!')
        continue
    
    size = Path(db_path).stat().st_size
    print(f'  Size: {size / 1024:.1f} KB')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check what tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f'  Tables: {tables}')
    
    if not tables:
        print('  (no tables)')
    else:
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f'\n  {table}: {count} rows')
            
            if count > 0 and count <= 5:
                cursor.execute(f'SELECT * FROM {table} LIMIT 3')
                for row in cursor.fetchall():
                    print(f'    {row}')
    
    conn.close()
