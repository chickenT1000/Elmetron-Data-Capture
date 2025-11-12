"""Test the operators API endpoint."""
import sqlite3

# Check database
conn = sqlite3.connect('data/elmetron.sqlite')
conn.row_factory = sqlite3.Row

print("Testing operators query...")
print()

operators = conn.execute("""
    SELECT DISTINCT operator_name 
    FROM sessions 
    WHERE operator_name IS NOT NULL AND operator_name != ''
    ORDER BY operator_name ASC
""").fetchall()

print(f"Found {len(operators)} operator(s) in database:")
for op in operators:
    print(f"  - '{op['operator_name']}'")

print()
print("All sessions with operator_name:")
sessions = conn.execute("""
    SELECT id, started_at, operator_name 
    FROM sessions 
    WHERE operator_name IS NOT NULL
    ORDER BY started_at DESC
    LIMIT 10
""").fetchall()

for s in sessions:
    print(f"  Session {s['id']}: '{s['operator_name']}' (started: {s['started_at']})")

conn.close()

print()
print("Testing API endpoint...")
import requests
try:
    response = requests.get('http://127.0.0.1:8050/api/operators')
    print(f"Status: {response.status_code}")
    if response.ok:
        data = response.json()
        print(f"API returned: {data}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Failed to connect: {e}")
