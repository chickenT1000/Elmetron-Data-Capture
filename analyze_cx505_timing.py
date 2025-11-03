#!/usr/bin/env python3
"""
Analyze CX-505 measurement timing to determine:
1. Actual device sampling rate
2. Timestamp precision in real data
3. Storage savings from precision reduction
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import Counter
import statistics

db_path = Path("data/elmetron.sqlite")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=" * 80)
print("CX-505 TIMING ANALYSIS")
print("=" * 80)

# Get a recent session with good amount of data
cursor.execute("""
    SELECT id, started_at, ended_at, 
           (SELECT COUNT(*) FROM measurements WHERE session_id = sessions.id) as meas_count
    FROM sessions 
    WHERE (SELECT COUNT(*) FROM measurements WHERE session_id = sessions.id) > 100
    ORDER BY id DESC 
    LIMIT 1
""")
session = cursor.fetchone()

if not session:
    print("No sessions with sufficient data found")
    conn.close()
    exit(1)

session_id, started_at, ended_at, meas_count = session
print(f"\nAnalyzing Session {session_id}:")
print(f"  Started: {started_at}")
print(f"  Ended: {ended_at}")
print(f"  Measurements: {meas_count}")

# Get consecutive measurements with timestamps
cursor.execute("""
    SELECT 
        id,
        measurement_timestamp,
        value,
        unit
    FROM measurements 
    WHERE session_id = ? 
        AND measurement_timestamp IS NOT NULL
    ORDER BY id ASC
    LIMIT 500
""", (session_id,))

measurements = cursor.fetchall()

if len(measurements) < 10:
    print("Not enough measurements with timestamps")
    conn.close()
    exit(1)

print(f"\n{'=' * 80}")
print("TIMESTAMP PRECISION ANALYSIS")
print("=" * 80)

# Parse timestamps and analyze precision
timestamps = []
timestamp_strings = []
has_milliseconds = 0
has_microseconds = 0
whole_seconds = 0

for meas_id, ts_str, value, unit in measurements[:100]:  # First 100
    timestamp_strings.append(ts_str)
    
    # Check precision in string format
    if ts_str:
        if '.' in ts_str:
            fractional = ts_str.split('.')[-1].rstrip('Z')
            frac_len = len(fractional)
            if frac_len >= 6:
                has_microseconds += 1
            elif frac_len >= 3:
                has_milliseconds += 1
        else:
            whole_seconds += 1
        
        # Parse to datetime
        try:
            # Handle various formats
            if ts_str.endswith('Z'):
                ts_str_clean = ts_str.rstrip('Z')
            else:
                ts_str_clean = ts_str
            
            if '.' in ts_str_clean:
                dt = datetime.fromisoformat(ts_str_clean)
            else:
                dt = datetime.fromisoformat(ts_str_clean)
            
            timestamps.append(dt)
        except:
            pass

print(f"\nTimestamp Format Analysis (first 100 measurements):")
print(f"  Whole seconds only: {whole_seconds}")
print(f"  With milliseconds:  {has_milliseconds}")
print(f"  With microseconds:  {has_microseconds}")

print(f"\nSample timestamps:")
for i, ts in enumerate(timestamp_strings[:10]):
    print(f"  {i+1:3d}. {ts}")

# Calculate time deltas between consecutive measurements
if len(timestamps) >= 2:
    deltas = []
    for i in range(1, len(timestamps)):
        delta = (timestamps[i] - timestamps[i-1]).total_seconds()
        deltas.append(delta)
    
    print(f"\n{'=' * 80}")
    print("SAMPLING RATE ANALYSIS")
    print("=" * 80)
    
    print(f"\nTime between consecutive measurements (first 20):")
    for i, delta in enumerate(deltas[:20]):
        print(f"  {i+1:3d}. {delta:10.6f} seconds")
    
    # Statistics
    min_delta = min(deltas)
    max_delta = max(deltas)
    avg_delta = statistics.mean(deltas)
    median_delta = statistics.median(deltas)
    
    # Count deltas by rounding
    delta_distribution = Counter()
    for d in deltas:
        rounded = round(d, 3)  # Round to milliseconds
        delta_distribution[rounded] += 1
    
    print(f"\nStatistics:")
    print(f"  Min delta:    {min_delta:.6f} seconds")
    print(f"  Max delta:    {max_delta:.6f} seconds")
    print(f"  Average:      {avg_delta:.6f} seconds")
    print(f"  Median:       {median_delta:.6f} seconds")
    print(f"  Sampling rate: ~{1/avg_delta:.2f} Hz (avg), ~{1/median_delta:.2f} Hz (median)")
    
    print(f"\nMost common intervals (top 10):")
    for delta, count in delta_distribution.most_common(10):
        hz = 1/delta if delta > 0 else 0
        print(f"  {delta:8.3f}s ({hz:6.2f} Hz): {count:4d} occurrences ({count/len(deltas)*100:.1f}%)")

# Storage analysis
print(f"\n{'=' * 80}")
print("STORAGE ANALYSIS")
print("=" * 80)

cursor.execute("""
    SELECT 
        COUNT(*) as total_measurements,
        AVG(LENGTH(measurement_timestamp)) as avg_ts_length
    FROM measurements
    WHERE measurement_timestamp IS NOT NULL
""")
total_meas, avg_len = cursor.fetchone()

print(f"\nDatabase-wide statistics:")
print(f"  Total measurements with timestamps: {total_meas:,}")
print(f"  Average timestamp length: {avg_len:.2f} bytes")

# Calculate storage for different precision levels
current_storage = total_meas * avg_len

# ISO format examples:
# 2025-10-01T12:25:56Z           (20 bytes) - whole seconds
# 2025-10-01T12:25:56.123Z       (24 bytes) - milliseconds
# 2025-10-01T12:25:56.123456Z    (27 bytes) - microseconds

print(f"\nCurrent storage:")
print(f"  Timestamps: {current_storage:,} bytes ({current_storage/1024/1024:.2f} MB)")

# Estimate storage if all were whole seconds (20 bytes)
whole_sec_storage = total_meas * 20
savings = current_storage - whole_sec_storage

print(f"\nIf all timestamps were whole seconds (20 bytes):")
print(f"  Timestamps: {whole_sec_storage:,} bytes ({whole_sec_storage/1024/1024:.2f} MB)")
print(f"  Savings: {savings:,} bytes ({savings/1024/1024:.2f} MB, {savings/current_storage*100:.1f}%)")

# Estimate if using milliseconds (24 bytes)
millisec_storage = total_meas * 24
millisec_savings = current_storage - millisec_storage

print(f"\nIf all timestamps had milliseconds (24 bytes):")
print(f"  Timestamps: {millisec_storage:,} bytes ({millisec_storage/1024/1024:.2f} MB)")
print(f"  Savings: {millisec_savings:,} bytes ({millisec_savings/1024/1024:.2f} MB, {millisec_savings/current_storage*100:.1f}%)")

# Check offset_seconds precision in session evaluation context
print(f"\n{'=' * 80}")
print("OFFSET CALCULATION PRECISION ANALYSIS")
print("=" * 80)

if len(timestamps) >= 2:
    anchor = timestamps[0]
    offsets = [(ts - anchor).total_seconds() for ts in timestamps[:50]]
    
    print(f"\nOffset from first measurement (first 20):")
    for i, offset in enumerate(offsets[:20]):
        rounded = round(offset)
        diff = offset - rounded
        print(f"  {i+1:3d}. Raw: {offset:12.9f}s, Rounded: {rounded:4d}s, Diff: {diff:+.9f}s")
    
    # Check how many offsets would change with rounding
    significant_changes = sum(1 for o in offsets if abs(o - round(o)) > 0.1)
    print(f"\nRounding impact:")
    print(f"  Offsets analyzed: {len(offsets)}")
    print(f"  Would change by >0.1s: {significant_changes} ({significant_changes/len(offsets)*100:.1f}%)")

conn.close()

print(f"\n{'=' * 80}")
print("RECOMMENDATION")
print("=" * 80)
print("""
Based on the analysis above:

1. Device Sampling Rate: Check the actual Hz reported above
2. Timestamp Precision: Check what the device is actually sending
3. Storage Impact: Check savings percentage

RECOMMENDATIONS will be printed based on the data...
""")
