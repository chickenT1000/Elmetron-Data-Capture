# Conductivity Chart Scaling Issue - Root Cause Analysis

## Problem Statement

When the conductivity electrode is removed from solution:
- **Conductivity drops to near-zero** (0.33 µS/cm in our case)
- **Chart autoscaling includes this value** in range calculation
- **Y-axis scales to 0-1000 µS/cm** (or even 0-500,000 µS/cm)
- **Normal data (~542 µS/cm) appears as a flat line** near bottom of chart

## Current Data Analysis

```
Min: 0.33 µS/cm     ← Electrode OUT of solution
Max: 549.50 µS/cm   ← Normal measurement
Mean: 532.86 µS/cm  
Median: 543.80 µS/cm ← Actual typical value
Current: ~542-543 µS/cm ← Stable reading
```

## Root Cause

The autoscaling logic in `useChartAutoScaling.ts`:

```typescript
const validData = data
  .map(d => d[dataKey])
  .filter((val): val is number => val !== null && val !== undefined && !isNaN(val));

const dataMin = Math.min(...validData);  // ← Includes 0.33!
const dataMax = Math.max(...validData);
```

**The issue:** Treats 0.33 µS/cm (electrode out) as a valid measurement!

## Why This Happens

1. **Electrode out of solution** → Device reads near-zero or air conductivity
2. **All numeric values are considered valid** → 0.33 is technically a valid number
3. **Autoscaling includes full range** → Scales from 0.33 to 549.50
4. **Chart selects preset** → Chooses "0-1000 µS/cm" or wider
5. **Normal data compressed** → 542 µS/cm looks flat

## NOT About Polarization

**Initial misunderstanding:** We thought it was about polarization spikes during electrode immersion

**Actual issue:** It's about **electrode OUT of solution** giving unrealistic low values

The rate-of-change filtering we implemented won't help here because:
- Removing electrode is slow and gradual (not a rapid spike)
- The problem is LOW values, not HIGH spikes
- Filter would remove the transition, but keep the zero values

## Solutions (In Order of Preference)

### Option 1: Smart Minimum Threshold ✅ RECOMMENDED

**Exclude unrealistically low values from autoscaling:**

```typescript
// For conductivity: values < 10 µS/cm are likely "electrode out"
const MIN_REALISTIC_CONDUCTIVITY = 10;  // µS/cm

const validData = data
  .map(d => d[dataKey])
  .filter((val): val is number => {
    if (val === null || val === undefined || isNaN(val)) return false;
    
    // Special handling for conductivity: exclude "electrode out" values
    if (dataKey === 'conductivity' && val < MIN_REALISTIC_CONDUCTIVITY) {
      return false;  // Don't include in scaling calculation
    }
    
    return true;
  });
```

**Pros:**
- Simple and effective
- Autoscaling works correctly for realistic data
- Low values still stored in database (for reference)
- Chart gaps show when electrode is out (intentional)

**Cons:**
- Needs threshold tuning per parameter type
- Ultra-pure water might have conductivity < 10 µS/cm (rare)

### Option 2: Minimum Scale Range

**Never let conductivity scale go below a certain range:**

```typescript
// After selecting preset
if (dataKey === 'conductivity' && selectedPreset.max < 100) {
  // Force minimum useful range
  selectedPreset = presets.find(p => p.max >= 100) || selectedPreset;
}
```

**Pros:**
- Always shows a useful scale
- Simple fallback

**Cons:**
- Doesn't solve root cause
- Ultra-pure water measurements would look weird

### Option 3: Filter Out in Chart Display

**Don't render conductivity points below threshold:**

```typescript
// In chart component
const filteredData = data.map(d => ({
  ...d,
  conductivity: d.conductivity && d.conductivity >= MIN_THRESHOLD 
    ? d.conductivity 
    : null
}));
```

**Pros:**
- Clean chart display
- Clear visual indication (gaps) when electrode is out

**Cons:**
- Loses information about when electrode was removed
- Harder to debug issues

### Option 4: Separate "Electrode Connected" Logic

**Backend detects if electrode is physically connected:**

```typescript
// Check if reading is realistic for the electrode type
function isElectrodeConnected(value: number, type: string): boolean {
  if (type === 'conductivity') {
    return value >= MIN_REALISTIC_CONDUCTIVITY;
  }
  // pH: should be between 0-14
  // Redox: should be between -2000 to +2000
  return true;
}
```

**Pros:**
- Most accurate
- Can show "Electrode Disconnected" status
- Backend validation

**Cons:**
- More complex
- Requires API changes

## Recommended Approach

**Hybrid Solution: Option 1 + Option 3**

1. **In autoscaling logic:** Exclude unrealistic values from range calculation
2. **In chart display:** Show gaps when values are below threshold
3. **Add visual indicator:** "Electrode out of solution" message when values are low

### Thresholds Per Parameter

```typescript
const MIN_REALISTIC_VALUES = {
  conductivity: 10,        // µS/cm - below this is likely air or electrode out
  ph: 0,                   // pH - technically can be negative, but rare
  redox: -2000,            // mV - full valid range
  temperature: -50,        // °C - below this is likely sensor error
};

const MAX_REALISTIC_VALUES = {
  conductivity: 200000,    // µS/cm - above is likely seawater or error
  ph: 14,                  // pH - above is extremely rare
  redox: 2000,             // mV - full valid range
  temperature: 100,        // °C - above is boiling, likely error in normal use
};
```

### Implementation Steps

1. **Update `useChartAutoScaling.ts`:**
   - Add realistic value thresholds
   - Filter out unrealistic values from scaling calculation
   - Keep logic simple and fast

2. **Update chart display (optional):**
   - Show gaps when values are unrealistic
   - Add visual indicator for "out of range" status

3. **Test with real data:**
   - Remove electrode → Should show gap in chart
   - Reinsert electrode → Should resume with correct scale
   - Normal measurements → Should autoscale nicely

4. **Documentation:**
   - Explain why values are filtered
   - How to adjust thresholds if needed
   - What happens when electrode is out

## Expected Behavior After Fix

**Scenario 1: Normal Measurement**
- Conductivity: 542 µS/cm
- Chart scales to: 0-1000 µS/cm preset
- Display: Normal, data clearly visible ✅

**Scenario 2: Electrode Removed**
- Conductivity drops to: 0.33 µS/cm
- Chart: **Excludes from scaling** (value < 10 µS/cm)
- Chart: Shows gap (no data point rendered)
- Scale: **Remains at previous range** (e.g., 0-1000 µS/cm)
- Display: Gap shows electrode is out ✅

**Scenario 3: Electrode Reinserted**
- Conductivity: Rises through 50, 200, 400, 540 µS/cm
- Chart: Starts showing data again when > 10 µS/cm
- Autoscaling: Recalculates based on valid values
- Display: Smooth transition back to measurement ✅

## Why This Is Better Than Rate-of-Change Filtering

**Rate-of-change filtering (what we just implemented):**
- ✗ Doesn't help with electrode removal (gradual change)
- ✗ Still includes zero values in autoscaling
- ✗ Adds complexity without solving the root issue
- ✓ Good for rapid polarization spikes (different problem)

**Realistic value filtering (this solution):**
- ✓ Directly addresses the root cause
- ✓ Simple threshold logic
- ✓ Fast and efficient
- ✓ Works for all scenarios (electrode in/out)
- ✓ No false positives on normal data

## Implementation Priority

1. **High Priority:** Fix autoscaling to exclude unrealistic values
2. **Medium Priority:** Add visual gaps for out-of-range values
3. **Low Priority:** Add "Electrode Status" indicator in UI
4. **Optional:** Keep rate-of-change filter for polarization (if actually needed)

## Testing Plan

1. **Test with electrode in solution:** Normal behavior, good scaling
2. **Test with electrode out:** Gap in chart, scale doesn't jump to 500k
3. **Test rapid removal/insertion:** Smooth transitions
4. **Test ultra-pure water:** Adjust threshold if < 10 µS/cm is valid
5. **Test other parameters:** Ensure filtering doesn't affect pH, redox, temp

## Conclusion

**Root cause:** Including zero/near-zero conductivity values (electrode out) in autoscaling

**Solution:** Filter out unrealistic values from autoscaling calculations

**Result:** Charts scale correctly for actual measurements, show gaps when electrode is out

This is a **data quality** issue, not a filtering/smoothing issue. The fix should be in the autoscaling logic, not in signal processing.
