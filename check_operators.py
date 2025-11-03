import sqlite3

conn = sqlite3.connect('data/elmetron.sqlite')
cursor = conn.cursor()

# Check sessions table structure
cursor.execute("PRAGMA table_info(sessions)")
columns = cursor.fetchall()
print("Sessions table columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n" + "="*50 + "\n")

# Check distinct operator names
cursor.execute("""
    SELECT DISTINCT operator_name 
    FROM sessions 
    WHERE operator_name IS NOT NULL AND operator_name != ''
    ORDER BY operator_name
""")
operators = cursor.fetchall()
print(f"Found {len(operators)} distinct operators:")
for op in operators:
    print(f"  - '{op[0]}'")

print("\n" + "="*50 + "\n")

# Check all operator names (including nulls/empty)
cursor.execute("SELECT id, started_at, operator_name FROM sessions ORDER BY id DESC LIMIT 10")
recent = cursor.fetchall()
print("Recent 10 sessions:")
for row in recent:
    print(f"  ID: {row[0]}, Started: {row[1]}, Operator: {repr(row[2])}")

conn.close()
