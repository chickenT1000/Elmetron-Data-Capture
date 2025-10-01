import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/elmetron.sqlite')
cursor = conn.cursor()

# Check recent sessions
print('='*60)
print('RECENT SESSIONS (last 5)')
print('='*60)
cursor.execute('''
    SELECT s.id, s.started_at, s.ended_at, s.note, i.serial
    FROM sessions s
    LEFT JOIN instruments i ON s.instrument_id = i.id
    ORDER BY s.started_at DESC 
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f'  Session {row[0]}: Started {row[1]}')
    print(f'    End: {row[2] or "ACTIVE"}, Device S/N: {row[4]}, Note: {row[3] or "none"}')

# Check measurement counts per session
print('\n' + '='*60)
print('MEASUREMENT COUNTS PER SESSION')
print('='*60)
cursor.execute('''
    SELECT session_id, MIN(measurement_timestamp) as first_meas, MAX(measurement_timestamp) as last_meas, COUNT(*) as count 
    FROM measurements 
    GROUP BY session_id 
    ORDER BY session_id DESC 
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f'  Session {row[0]}: {row[3]} measurements ({row[1]} to {row[2]})')

# Check if data is recent (within last 10 minutes)
print('\n' + '='*60)
print('DATA FRESHNESS CHECK')
print('='*60)
cursor.execute('''
    SELECT MAX(measurement_timestamp) as latest_measurement 
    FROM measurements
''')
latest = cursor.fetchone()[0]
if latest:
    print(f'  Latest measurement: {latest}')
    # Parse the timestamp (assuming ISO format)
    try:
        latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
        now = datetime.now(latest_dt.tzinfo)
        age_seconds = (now - latest_dt).total_seconds()
        print(f'  Age: {age_seconds:.1f} seconds ago')
        if age_seconds < 60:
            print('  ✓ Data is FRESH (less than 1 minute old)')
        elif age_seconds < 600:
            print(f'  ⚠ Data is {age_seconds/60:.1f} minutes old')
        else:
            print(f'  ✗ Data is STALE ({age_seconds/60:.1f} minutes old)')
    except Exception as e:
        print(f'  (Could not parse timestamp: {e})')
else:
    print('  ✗ No measurements in database')

conn.close()
