import sqlite3
from pathlib import Path

db_path = Path("data/elmetron.sqlite")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("Checking for extreme conductivity values in session 83...")
print("=" * 70)

# Get overall stats
cursor.execute("""
    SELECT MAX(value) as max_val, MIN(value) as min_val, AVG(value) as avg_val, COUNT(*) as count
    FROM measurements 
    WHERE session_id=83 AND (unit LIKE '%S/cm%' OR unit LIKE '%s/cm%')
""")
row = cursor.fetchone()
print(f"\nSession 83 conductivity statistics:")
print(f"  Count: {row[3]}")
print(f"  MIN:   {row[1]:.2f} uS/cm")
print(f"  MAX:   {row[0]:.2f} uS/cm")
print(f"  AVG:   {row[2]:.2f} uS/cm")

# Check for extreme high values
print(f"\n{'='*70}")
print("Values > 1000 uS/cm (should be none for normal water):")
print(f"{'='*70}")
cursor.execute("""
    SELECT value, unit, datetime(created_at, 'localtime') as ts
    FROM measurements 
    WHERE session_id=83 
    AND (unit LIKE '%S/cm%' OR unit LIKE '%s/cm%')
    AND value > 1000
    ORDER BY value DESC
    LIMIT 30
""")
rows = cursor.fetchall()
if rows:
    print(f"{'Value':>12} | {'Unit':<10} | {'Timestamp'}")
    print("-" * 70)
    for r in rows:
        print(f"{r[0]:>12.2f} | {r[1]:<10} | {r[2]}")
else:
    print("No values > 1000 found (good!)")

# Check for extremely high values
print(f"\n{'='*70}")
print("Values > 10000 uS/cm (extreme outliers):")
print(f"{'='*70}")
cursor.execute("""
    SELECT value, unit, datetime(created_at, 'localtime') as ts
    FROM measurements 
    WHERE session_id=83 
    AND (unit LIKE '%S/cm%' OR unit LIKE '%s/cm%')
    AND value > 10000
    ORDER BY value DESC
    LIMIT 20
""")
rows = cursor.fetchall()
if rows:
    print(f"{'Value':>12} | {'Unit':<10} | {'Timestamp'}")
    print("-" * 70)
    for r in rows:
        print(f"{r[0]:>12.2f} | {r[1]:<10} | {r[2]}")
else:
    print("No extreme values > 10000 found")

# Check recent values (last 50)
print(f"\n{'='*70}")
print("Most recent 20 conductivity readings:")
print(f"{'='*70}")
cursor.execute("""
    SELECT value, unit, datetime(created_at, 'localtime') as ts
    FROM measurements 
    WHERE session_id=83 
    AND (unit LIKE '%S/cm%' OR unit LIKE '%s/cm%')
    ORDER BY created_at DESC
    LIMIT 20
""")
rows = cursor.fetchall()
print(f"{'Value':>12} | {'Unit':<10} | {'Timestamp'}")
print("-" * 70)
for r in rows:
    print(f"{r[0]:>12.2f} | {r[1]:<10} | {r[2]}")

# Check for mS/cm vs uS/cm unit confusion
print(f"\n{'='*70}")
print("Checking unit types:")
print(f"{'='*70}")
cursor.execute("""
    SELECT unit, COUNT(*) as count, AVG(value) as avg_value, MIN(value), MAX(value)
    FROM measurements 
    WHERE session_id=83 
    AND (unit LIKE '%S/cm%' OR unit LIKE '%s/cm%')
    GROUP BY unit
""")
rows = cursor.fetchall()
print(f"{'Unit':<15} | {'Count':>8} | {'Avg Value':>12} | {'Min':>10} | {'Max':>10}")
print("-" * 70)
for r in rows:
    print(f"{r[0]:<15} | {r[1]:>8} | {r[2]:>12.2f} | {r[3]:>10.2f} | {r[4]:>10.2f}")

conn.close()
