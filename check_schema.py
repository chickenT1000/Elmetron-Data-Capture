import sqlite3

conn = sqlite3.connect('data/elmetron.sqlite')

print("audit_events columns:")
for row in conn.execute('PRAGMA table_info(audit_events)').fetchall():
    print(f"  - {row[1]} ({row[2]})")

print("\nmarkers table exists:", conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='markers'").fetchone() is not None)

if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='markers'").fetchone():
    print("\nmarkers columns:")
    for row in conn.execute('PRAGMA table_info(markers)').fetchall():
        print(f"  - {row[1]} ({row[2]})")

conn.close()
