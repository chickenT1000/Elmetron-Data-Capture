import sqlite3
from pathlib import Path

db_path = Path("data/elmetron.sqlite")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("Sessions table schema:")
print("=" * 70)
cursor.execute('PRAGMA table_info(sessions)')
cols = cursor.fetchall()
for col in cols:
    nullable = "NULL" if not col[3] else "NOT NULL"
    pk = "PK" if col[5] else ""
    print(f"  {col[1]:<20} {col[2]:<15} {nullable:<10} {pk}")

print("\n" + "=" * 70)
print("Recent sessions (last 5):")
print("=" * 70)
cursor.execute('SELECT id, started_at, ended_at, note FROM sessions ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()
for r in rows:
    print(f"  ID: {r[0]:<5} Started: {r[1]:<25} Note: {r[3]}")

# Check if there's operator information anywhere
print("\n" + "=" * 70)
print("Checking for operator information...")
print("=" * 70)

# Try to find operator in different places
cursor.execute('SELECT id, note FROM sessions WHERE note IS NOT NULL LIMIT 3')
rows = cursor.fetchall()
if rows:
    print("Sessions with notes:")
    for r in rows:
        print(f"  ID: {r[0]}, Note: {r[1]}")

conn.close()
