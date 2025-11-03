# CX-505 Device Timing Analysis - Results & Recommendations

## Key Findings

### 1. Device Sampling Rate
**CX-505 samples at exactly 1 Hz (1 measurement per second)**

Evidence:
- 82.8% of measurements are exactly 1.000 seconds apart
- 16.2% are 2.000 seconds apart (occasional missed readings)
- Median interval: 1.000 seconds
- **Device is NOT sending sub-second measurements**

### 2. Timestamp Precision from Device
**Device sends WHOLE SECOND timestamps (99% of the time)**

Evidence:
```
Sample timestamps from device:
  2025-11-03T07:00:57.690Z  ← Only 1 out of 100 had milliseconds!
  2025-11-03T08:54:30       ← Rest are whole seconds
  2025-11-03T08:54:31
  2025-11-03T08:54:33
  2025-11-03T08:54:34
  ...
```

**Conclusion:** CX-505 is already sending whole second data. No sub-second precision to preserve!

### 3. The Fractional Offset Problem - ROOT CAUSE IDENTIFIED

**Problem:** User sees `-0.31666666666666665` in offsets

**Why it happens:**
```
First measurement:  2025-11-03T07:00:57.690Z  ← Has .690 milliseconds
Second measurement: 2025-11-03T08:54:30       ← Whole second

Offset calculation:
  (08:54:30.000 - 07:00:57.690) = 6812.310 seconds
                                         ^^^
                                  This .310 propagates to ALL offsets!
```

**All subsequent offsets have +0.310 because of ONE timestamp with milliseconds!**

### 4. Storage Analysis

**Current State:**
- Total measurements: 110,887
- Average timestamp: 19.07 bytes
- Total storage: 2.02 MB

**Storage Options:**
- Force whole seconds (20 bytes): Would INCREASE by 0.10 MB (no savings!)
- Force milliseconds (24 bytes): Would INCREASE by 0.52 MB (worse!)

**Conclusion:** Database is already optimally storing data. No storage savings possible.

## Root Cause Summary

The fractional seconds in offsets are NOT from:
- ❌ Device sending high-frequency data
- ❌ Device sending sub-second precision
- ❌ Database storing unnecessary precision

The fractional seconds ARE from:
- ✅ Python float arithmetic when calculating time differences
- ✅ Occasional timestamps with milliseconds used as anchors
- ✅ Float representation of whole numbers (e.g., 1.0 instead of 1)

## Recommendations

### Option 1: Round Offsets Only (Display) ⭐ RECOMMENDED
**What:** Round `offset_seconds` to whole seconds when calculating/displaying

**Why:**
- Device is already sending 1 Hz data
- No sub-second precision to preserve
- Matches device's actual capability
- No data migration needed
- Clean user interface

**Implementation:**
```python
# Backend: When calculating offsets
offset_seconds = round((timestamp - anchor_ts).total_seconds())

# Frontend: Display formatting
const formatOffset = (value: number) => {
  return `${Math.round(value)}s`;
};
```

**Impact:**
- ✅ Fixes user's issue immediately
- ✅ No data loss (device isn't sending sub-second data anyway)
- ✅ Matches device's 1 Hz capability
- ✅ Clean display: `-1s`, `+5s`, `+2m 30s`

### Option 2: Strip Milliseconds from Timestamps (Storage)
**What:** Remove milliseconds when storing timestamps

**Why:**
- Device rarely sends them (1 in 100)
- They cause offset calculation issues
- Would make data more consistent

**Implementation:**
```python
# When storing measurement
if '.' in timestamp_str:
    timestamp_str = timestamp_str.split('.')[0] + 'Z'
```

**Impact:**
- ✅ Prevents anchor timestamp from having milliseconds
- ✅ All offsets would be whole numbers naturally
- ⚠️ Loses the occasional millisecond from device (rare)
- ⚠️ Requires code change in capture system

### Option 3: Hybrid (Best Long-term) ⭐⭐ BEST
**Combine both approaches:**

1. **Backend:** Round offsets when calculating
2. **Capture System:** Strip milliseconds when storing (optional)
3. **Frontend:** Display whole seconds

**Why Best:**
- Immediate fix (rounding)
- Clean data going forward (strip milliseconds)
- Matches device capability (1 Hz)
- No migration of existing data

## Detailed Recommendation

### Phase 1: Fix Display (Immediate - 30 minutes)

**Backend changes:**
```python
# elmetron/reporting/session.py, line 228
if timestamp and anchor_ts:
    offset_seconds = round((timestamp - anchor_ts).total_seconds())
    offsets.append(offset_seconds)

# Line 252 - marker offsets
if _is_calibration_record(record):
    markers.append({
        'type': 'calibration',
        'timestamp': measurement_ts,
        'offset_seconds': round(offset_seconds) if offset_seconds is not None else None,
        'measurement_id': record.get('measurement_id'),
    })
```

**Frontend changes:**
```typescript
// ui/src/pages/SessionEvaluationPage.tsx
const formatOffset = (value?: number | null): string => {
  if (value === undefined || value === null) return '—';
  const rounded = Math.round(value);
  const sign = rounded > 0 ? '+' : rounded < 0 ? '−' : '';
  const abs = Math.abs(rounded);
  
  if (abs >= 60) {
    const minutes = Math.floor(abs / 60);
    const seconds = abs % 60;
    return seconds > 0 ? `${sign}${minutes}m ${seconds}s` : `${sign}${minutes}m`;
  }
  return `${sign}${abs}s`;
};
```

### Phase 2: Clean Future Data (Optional - 15 minutes)

**Capture system:**
```python
# elmetron/storage/database.py, line ~728
measurement_timestamp = measurement.get('timestamp') or decoded.get('captured_at')

# Add: Strip milliseconds for consistency
if measurement_timestamp and '.' in measurement_timestamp:
    # Keep only whole seconds
    measurement_timestamp = measurement_timestamp.split('.')[0]
    if not measurement_timestamp.endswith('Z'):
        measurement_timestamp += 'Z'
```

## Answer to Your Questions

### Q1: "What is the CX-505 refresh rate?"
**A: Exactly 1 Hz (1 measurement per second)**

Evidence: 82.8% of intervals are exactly 1.000 seconds, median is 1.000 seconds.

### Q2: "Preserve all data CX-505 is sending?"
**A: We already are!**

Device sends:
- 1 measurement per second
- Whole second timestamps (99% of time)
- Occasionally one timestamp with milliseconds

We're storing everything the device sends. No data loss.

### Q3: "Would removing precision save space?"
**A: NO - would actually INCREASE storage!**

Current: 19.07 bytes average (optimal)
Whole seconds: 20 bytes (0.10 MB more)
Milliseconds: 24 bytes (0.52 MB more)

### Q4: "Are we storing unnecessary precision?"
**A: NO - device isn't sending sub-second data**

The fractional offsets come from:
- Float arithmetic in Python
- Occasional millisecond in anchor timestamp
- NOT from device sending high-precision data

## Final Recommendation

✅ **Implement Phase 1 (Round offsets) immediately**
- Solves user's display issue
- No data loss (device sends 1 Hz anyway)
- 30 minutes to implement
- Matches device's actual capability

✅ **Optionally implement Phase 2 (Strip milliseconds)**
- Prevents future fractional offsets
- Makes data more consistent
- 15 minutes to implement
- Device rarely sends milliseconds anyway

❌ **Do NOT modify timestamp storage format**
- Already optimal
- No space savings
- Would increase complexity

## Summary

**Device Reality:**
- CX-505 samples at 1 Hz
- Sends whole second timestamps
- No sub-second precision exists

**Problem:**
- Fractional offsets from Python float arithmetic
- Occasional millisecond in anchor timestamp

**Solution:**
- Round offsets to match device capability
- Optionally strip rare milliseconds
- Keep storage format as-is

**Result:**
- User sees clean offsets: `-1s`, `+5s`, `+2m 30s`
- No data loss (device doesn't send sub-second data)
- No storage overhead
- Implementation: 30-45 minutes

---

## Approve to proceed with Phase 1 (Round offsets)?
This will immediately fix the display issue while preserving all real device data.
