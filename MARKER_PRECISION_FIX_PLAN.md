# Marker Placement Precision - Analysis & Fix Plan

## Problem Statement

**User Report:**
When placing markers, sees overly precise values like `-0.31666666666666665` seconds.

**Expected:**
- Precision up to 1 second (whole seconds)
- If marker snaps to data point, round the value
- Question: Are we storing unnecessary precision in database?

## Root Cause Analysis

### 1. Database Storage Investigation

**Current State:**
```sql
measurement_timestamp TEXT  -- Stored as ISO string
```

**Sample Data:**
```
2025-10-01T12:25:56.608Z    -- Has milliseconds (.608)
2025-10-01T14:20:16         -- Whole seconds only
2025-10-01T14:20:17         -- Whole seconds only
```

**Finding:** 
- Database stores timestamps as TEXT in ISO format
- Some have millisecond precision (.608), some don't
- This is coming from the device/capture system
- Storage precision is INCONSISTENT

### 2. Offset Calculation

**Location:** `elmetron/reporting/session.py` line 228
```python
offset_seconds = (timestamp - anchor_ts).total_seconds()
```

**Problem:**
- Python's `total_seconds()` returns float with microsecond precision
- Even if timestamps are whole seconds, calculations create fractional values
- Example: If data points are at 10:00:00 and 10:00:01, but anchor is at 10:00:00.500, offsets will be -0.5 and +0.5

**Finding:**
- The fractional precision comes from:
  1. Device timestamps with milliseconds
  2. Anchor timestamp calculations
  3. Float arithmetic precision

### 3. Display/Format

**Current:** No rounding applied before display
**Result:** Shows 15+ decimal places like `-0.31666666666666665`

## Analysis: Is Extra Precision Needed?

### Device Measurement Reality
- CX-505 device likely samples at ~1 Hz (1 measurement per second)
- Even if device timestamps have milliseconds, measurement frequency doesn't require it
- Sub-second precision is **not meaningful** for this application

### Use Cases
1. **Calibration Markers**: Don't need sub-second precision
2. **Session Alignment**: Aligning to nearest second is sufficient
3. **Overlay Comparison**: Second-level precision is adequate
4. **Data Export**: Could keep precision for completeness, but display should round

### Recommendation
**Round to whole seconds everywhere** - no need for fractional seconds in this application.

## Solution Options

### Option 1: Round at Display Only (Frontend)
**Pros:**
- Preserves raw data precision
- Easy to implement
- Can change precision later

**Cons:**
- Data still transferred with high precision
- Charts might still use fractional values

**Implementation:**
```tsx
const formatOffset = (value?: number | null): string => {
  if (value === undefined || value === null) return '—';
  const rounded = Math.round(value);  // Round to nearest second
  // ... rest of formatting
};
```

### Option 2: Round at API Response (Backend)
**Pros:**
- Reduces data transfer
- Consistent across all clients
- Still preserves raw DB data

**Cons:**
- Rounds even for exports (might not want that)

**Implementation:**
```python
# In session.py
offset_seconds = round((timestamp - anchor_ts).total_seconds())
```

### Option 3: Round at Storage (Database)
**Pros:**
- Clean data from the start
- Smallest storage size
- Most consistent

**Cons:**
- Loses original precision permanently
- Requires data migration

**Implementation:**
```python
# When storing timestamp
measurement_timestamp = datetime_obj.replace(microsecond=0).isoformat()
```

### Option 4: Hybrid Approach ⭐ **RECOMMENDED**
**Store raw precision + Round for display/analysis**

**Why:**
1. Keep raw data for potential future needs
2. Round for all user-facing features
3. Round when creating markers
4. Round when calculating offsets for evaluation

**Implementation:**
- Database: Keep as-is (preserves raw data)
- Backend API: Round offset_seconds to nearest second
- Frontend: Display rounded values
- Marker creation: Snap to nearest second

## Detailed Implementation Plan

### Phase 1: Backend Rounding (API Layer)

**File:** `elmetron/reporting/session.py`

**Change 1: Round offsets in evaluation**
```python
# Line 228 - Round offset calculation
if timestamp and anchor_ts:
    offset_seconds = round((timestamp - anchor_ts).total_seconds())
    offsets.append(offset_seconds)
```

**Change 2: Round marker offsets**
```python
# Line 252 - Round marker offsets
if _is_calibration_record(record):
    markers.append({
        'type': 'calibration',
        'timestamp': measurement_ts,
        'offset_seconds': round(offset_seconds) if offset_seconds is not None else None,
        'measurement_id': record.get('measurement_id'),
    })
```

**File:** `data_api_service.py`

**Change 3: Round in evaluation endpoint**
```python
# Lines 1274, 1284 - Round offset calculations
offset_seconds = round((ts - anchor_ts).total_seconds())
```

**Change 4: Round in marker creation**
```python
# Line 587 - Round when storing marker
offset_seconds = data.get('offset_seconds')
if offset_seconds is not None:
    offset_seconds = round(float(offset_seconds))
```

### Phase 2: Frontend Display

**File:** `ui/src/pages/SessionEvaluationPage.tsx`

**Change 1: Update formatOffset function**
```tsx
const formatOffset = (value?: number | null): string => {
  if (value === undefined || value === null) {
    return '—';
  }
  
  // Already rounded from backend, but ensure it's a whole number
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

**Change 2: Update formatDuration function**
```tsx
const formatDuration = (value?: number | null): string => {
  if (value === undefined || value === null) {
    return '—';
  }
  
  // Round to nearest second
  const rounded = Math.round(value);
  const abs = Math.abs(rounded);
  
  if (abs >= 3600) {
    const hours = Math.floor(abs / 3600);
    const minutes = Math.floor((abs % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
  if (abs >= 60) {
    const minutes = Math.floor(abs / 60);
    const seconds = abs % 60;
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  }
  return `${abs}s`;
};
```

### Phase 3: Chart Data (Optional)

**File:** `ui/src/pages/SessionEvaluationPage.tsx`

**Only if chart x-axis shows fractional values:**
```tsx
const chartData = useMemo(() => {
  // ... existing merge logic ...
  // After building point, round offset:
  const roundedOffset = Math.round(point.offset_seconds);
  // Use roundedOffset as key instead
}, [evaluations]);
```

## Testing Plan

### 1. Test Offset Display
- Place marker → Should show whole seconds: `-1s`, `+5s`, `+1m 30s`
- View existing markers → Should show rounded values
- Export data → Check if offsets are rounded

### 2. Test Session Alignment
- Align by start → Offsets should be whole seconds
- Align by calibration → Offsets should be whole seconds
- Check chart x-axis labels → Should show whole seconds

### 3. Test Marker Creation
- Create marker at specific time → Should snap to nearest second
- API stores rounded value → Verify in database

### 4. Test Edge Cases
- Marker at exactly 0.5s → Rounds to nearest even (0 or 1)
- Very long sessions → Duration shows hours/minutes correctly
- Negative offsets → Display with minus sign correctly

## Database Precision Question: Answer

**Question:** "Are we storing more data in database than needed?"

**Answer:** 
- **YES** - Millisecond precision is unnecessary for this application
- **BUT** - No need to migrate existing data
- **SOLUTION** - Round at calculation/display time (not storage)
- **BENEFIT** - Preserves raw data if ever needed, while showing clean UI

## Recommendation Summary

✅ **Implement Option 4 (Hybrid)**:
1. Keep database timestamps as-is (preserve raw data)
2. Round all offset_seconds calculations to nearest second (backend)
3. Format display values as whole seconds (frontend)
4. Snap marker placement to nearest second

✅ **Benefits**:
- Clean user interface (no fractional seconds)
- Preserves original data precision
- Consistent across all features
- Easy to implement (no migration needed)

✅ **Implementation Time**: ~1 hour

---

## Approval Questions

1. **Rounding method**: Round to nearest second? (0.4s → 0s, 0.5s → 1s)
2. **Chart display**: Should chart x-axis also show whole seconds only?
3. **Export data**: Should CSV exports also have rounded offsets?
4. **Future precision**: Any use case where sub-second precision would be needed?

Please approve to proceed with implementation!
