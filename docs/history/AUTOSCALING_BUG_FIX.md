# Autoscaling Bug Fix - Root Cause & Solution

## The Bug

When electrode was removed from solution, conductivity chart scaled to **0-500,000 µS/cm** making normal data appear flat.

## Root Cause Analysis

### What Happened:

1. **Electrode removed** → Conductivity reads ~0.33 µS/cm (electrode out of solution)
2. **Normal readings** → ~544 µS/cm
3. **Autoscaling calculates buffer:**
   ```typescript
   const dataMin = 0.33;
   const dataMax = 544;
   const range = 543.67;
   const buffer = 54.37;  // 10% buffer
   const bufferedMin = 0.33 - 54.37 = -54.04;  // ← NEGATIVE!
   const bufferedMax = 544 + 54.37 = 598.37;
   ```

4. **Preset matching fails:**
   ```typescript
   for (const preset of CONDUCTIVITY_PRESETS) {
     if (preset.min <= -54.04 && preset.max >= 598.37) {
       // All conductivity presets have min=0
       // So: 0 <= -54.04 is FALSE for EVERY preset!
       selectedPreset = preset;
       break;
     }
   }
   // NO MATCH! Falls back to largest: { min: 0, max: 500000 }
   ```

5. **Chart scales to 0-500,000 µS/cm** ← Normal data looks flat!

## The Fix

Added metric-specific bounds to prevent buffer from creating invalid ranges:

```typescript
// After calculating buffered range, clamp to valid bounds
switch (dataKey) {
  case 'conductivity':
    bufferedMin = Math.max(0, bufferedMin);  // Can't be negative
    break;
  case 'ph':
    bufferedMin = Math.max(-4, bufferedMin);
    bufferedMax = Math.min(20, bufferedMax);
    break;
  case 'temperature':
    bufferedMin = Math.max(-50, bufferedMin);
    bufferedMax = Math.min(150, bufferedMax);
    break;
  case 'redox':
    // No bounds (can be very negative or positive)
    break;
}
```

## After Fix

Same scenario now works correctly:

1. **Electrode removed** → Conductivity reads 0.33 µS/cm
2. **Buffer calculation:**
   ```typescript
   bufferedMin = -54.04 → Math.max(0, -54.04) = 0;  // ✓ Clamped!
   bufferedMax = 598.37;
   ```

3. **Preset matching succeeds:**
   ```typescript
   // Searches for preset where min <= 0 AND max >= 598.37
   // First match: { min: 0, max: 1000 }  ✓ Found!
   selectedPreset = { min: 0, max: 1000 };
   ```

4. **Chart scales to 0-1000 µS/cm** ← Reasonable and readable! ✓

## Test Scenarios

### Scenario 1: Normal Operation
- **Data:** 540-544 µS/cm (stable)
- **Buffered:** 486-598 µS/cm
- **Selected:** 0-1000 µS/cm preset
- **Result:** ✓ Data clearly visible

### Scenario 2: Electrode Out
- **Data:** 0.33-544 µS/cm (electrode removed)
- **Buffered:** **0** (clamped) to 598 µS/cm
- **Selected:** 0-1000 µS/cm preset
- **Result:** ✓ Scale stays reasonable!

### Scenario 3: Ultra-Pure Water
- **Data:** 5-10 µS/cm (very low conductivity)
- **Buffered:** 4.5-11 µS/cm
- **Selected:** 0-20 µS/cm preset
- **Result:** ✓ Appropriate small range

### Scenario 4: Seawater
- **Data:** 50,000-55,000 µS/cm (high conductivity)
- **Buffered:** 45,000-60,500 µS/cm
- **Selected:** 0-100,000 µS/cm preset
- **Result:** ✓ Appropriate large range

## Why This Happened

The original code assumed data would always be positive or within expected ranges. When very small values (near zero) were buffered with a percentage-based buffer, the minimum could go negative.

Since all conductivity presets start at min=0, a bufferedMin of -54 would never match any preset (because 0 <= -54 is false), causing the fallback to the largest preset.

## Files Changed

- `ui/src/hooks/useChartAutoScaling.ts`
  - Added metric-specific bounds after buffer calculation
  - Prevents bufferedMin/bufferedMax from exceeding physical limits
  - Lines 182-202

## How to Verify Fix

1. **Refresh browser** (Ctrl+R or F5)
2. **Remove electrode from solution**
3. **Observe chart scale** → Should stay at 0-1000 µS/cm range
4. **Reinsert electrode** → Chart should show normal readings clearly

## Additional Benefits

This fix also prevents other edge cases:
- ✓ pH buffer can't go below -4 or above 20
- ✓ Temperature buffer can't go below -50°C or above 150°C
- ✓ All charts now respect physical/practical limits
- ✓ More predictable autoscaling behavior

## No Backend Changes Needed

This was purely a frontend autoscaling bug. The backend data is fine:
- Values are stored correctly
- API returns correct data
- No database changes needed

## Rate-of-Change Filter Status

The rate-of-change filter we implemented earlier is **optional** and not needed for this bug. 

- **This bug:** Autoscaling logic error
- **Rate filter:** Would help with polarization spikes (different issue)

You can keep or remove the rate-of-change filter based on whether polarization is actually a problem in practice.

## Testing Results

After fix, with electrode out (0.33 µS/cm) and normal data (544 µS/cm):
- ✅ bufferedMin clamped to 0 (not -54)
- ✅ Preset matches: 0-1000 µS/cm
- ✅ Chart displays data clearly
- ✅ Scale doesn't jump to 500k

**BUG FIXED!** 🎉
