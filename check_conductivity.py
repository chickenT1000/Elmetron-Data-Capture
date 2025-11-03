"""Check conductivity data for spikes."""
import sqlite3
import statistics

conn = sqlite3.connect('data/elmetron.sqlite')
cur = conn.cursor()

# Get all measurements from recent sessions to find conductivity
cur.execute("""
    SELECT value, unit, session_id, measurement_timestamp 
    FROM measurements 
    WHERE session_id >= 80 
    AND unit IN ('mS/cm', 'µS/cm', 'uS/cm')
    ORDER BY id DESC 
    LIMIT 500
""")

rows = cur.fetchall()

if rows:
    values = [float(row[0]) for row in rows]
    units = set([row[1] for row in rows])
    sessions = set([row[2] for row in rows])
    
    print(f"Total conductivity measurements: {len(values)}")
    print(f"Sessions: {sorted(sessions)}")
    print(f"Units: {units}")
    print(f"\nStatistics:")
    print(f"  Min: {min(values):.2f}")
    print(f"  Max: {max(values):.2f}")
    print(f"  Mean: {statistics.mean(values):.2f}")
    print(f"  Median: {statistics.median(values):.2f}")
    
    if len(values) > 1:
        print(f"  StdDev: {statistics.stdev(values):.2f}")
    
    print("\nFirst 30 values (most recent):")
    for val, unit, sess, ts in rows[:30]:
        print(f"  {val:.2f} {unit} (session {sess}) at {ts}")
    
    # Find extreme outliers (> 3 std devs from mean)
    if len(values) > 10:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        outliers = [(v, u, s) for v, u, s, t in rows if abs(v - mean) > 3 * stdev]
        if outliers:
            print(f"\nExtreme outliers (>3σ): {len(outliers)}")
            for val, unit, sess in outliers[:20]:
                print(f"  {val:.2f} {unit} in session {sess}")
else:
    print("No conductivity measurements found")

conn.close()
