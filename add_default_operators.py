import sqlite3

conn = sqlite3.connect('data/elmetron.sqlite')
cursor = conn.cursor()

# Update recent sessions with a default operator name
cursor.execute("""
    UPDATE sessions 
    SET operator_name = 'Admin' 
    WHERE operator_name IS NULL
""")

rows_updated = cursor.rowcount
conn.commit()

print(f"[OK] Updated {rows_updated} sessions with operator_name = 'Admin'")

# Verify the change
cursor.execute("""
    SELECT DISTINCT operator_name 
    FROM sessions 
    WHERE operator_name IS NOT NULL
    ORDER BY operator_name
""")
operators = cursor.fetchall()
print(f"\nFound {len(operators)} distinct operators:")
for op in operators:
    print(f"  - '{op[0]}'")

conn.close()
