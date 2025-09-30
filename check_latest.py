import sqlite3

conn = sqlite3.connect('data/elmetron.sqlite')
cursor = conn.cursor()

# Check sessions table
cursor.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT 3')
sessions = cursor.fetchall()
print('Latest sessions:')
for row in sessions:
    print(f'  {row}')

# Check measurements count
cursor.execute('SELECT COUNT(*) FROM measurements')
print(f'\nTotal measurements: {cursor.fetchone()[0]}')

# Check latest measurements
cursor.execute('SELECT * FROM measurements ORDER BY id DESC LIMIT 3')
measurements = cursor.fetchall()
print('\nLatest measurements:')
for row in measurements:
    print(f'  {row}')

conn.close()
