import sqlite3

conn = sqlite3.connect('data/elmetron.sqlite')
cursor = conn.cursor()

print('Sessions table schema:')
cursor.execute('PRAGMA table_info(sessions)')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

print('\nMeasurements table schema:')
cursor.execute('PRAGMA table_info(measurements)')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

conn.close()
