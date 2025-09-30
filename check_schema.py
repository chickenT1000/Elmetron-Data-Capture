import sqlite3

conn = sqlite3.connect('data/elmetron.sqlite')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(measurements)')
columns = cursor.fetchall()
print('Measurements table schema:')
for col in columns:
    print(f'  {col}')
conn.close()
