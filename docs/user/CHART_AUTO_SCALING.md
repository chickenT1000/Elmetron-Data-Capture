# Chart Auto-Scaling Feature

## Overview

The rolling charts feature includes intelligent auto-scaling that automatically adjusts the Y-axis range to fit your data while maintaining clean, readable grid lines. Instead of arbitrary scaling, the system selects from predefined preset ranges optimized for each measurement type.

## Key Benefits

- **Stable visualization**: Charts don't jump erratically as data changes
- **Clean grid lines**: Always shows even, readable numbers (no awkward decimals)
- **Optimized ranges**: Presets based on real-world measurement scenarios
- **Smart selection**: Automatically picks the smallest range that fits all data with buffer

## How Auto-Scaling Works

1. **Data Analysis**: System analyzes min/max values in the 10-minute window
2. **Buffer Addition**: Adds 10% padding above/below to avoid data touching edges
3. **Preset Selection**: Chooses the smallest preset range that contains buffered data
4. **Smooth Transitions**: Only changes scale when necessary (with hysteresis)

## Preset Ranges by Metric

### pH Scale
- **Minimum delta**: 1 pH unit
- **Maximum range**: -4 to 20 pH
- **Presets**:
  - 1 pH: [0-1], [1-2], [2-3], [3-4], [4-5], [5-6], [6-7], [7-8], [8-9], [9-10], [10-11], [11-12], [12-13], [13-14]
  - 2 pH: [0-2], [2-4], [4-6], [6-8], [8-10], [10-12], [12-14]
  - 4 pH: [0-4], [4-8], [8-12], [12-16]
  - 7 pH: [0-7], [7-14]
  - 14 pH: [0-14]
  - Full: [-4 to 20]

**Use cases**:
- Narrow ranges (1-2 pH): Precise monitoring during titrations, quality control
- Medium ranges (4-7 pH): General water analysis, process monitoring
- Full range: Extreme conditions, industrial applications

### Conductivity (µS/cm)
- **No negative values allowed**
- **Presets**:
  - Ultra-pure water: 0-10, 0-20, 0-50
  - Pure/distilled: 0-100, 0-200, 0-500
  - Drinking water: 0-1,000, 0-2,000
  - General water: 0-5,000, 0-10,000
  - High conductivity: 0-20,000, 0-50,000, 0-100,000
  - Seawater: 0-200,000
  - **Extreme (industrial/brine)**: 0-500,000

**Grid intervals**:
- 0-100: ticks every 20
- 0-1,000: ticks every 200
- 0-10,000: ticks every 2,000
- 0-100,000: ticks every 20,000
- 0-500,000: ticks every 100,000

### Redox/ORP (mV)
- **Can be positive or negative**
- **Presets**:
  - 200 mV ranges: [-200 to 0], [-100 to 100], [0 to 200]
  - 500 mV ranges: [-500 to 0], [-250 to 250], [0 to 500]
  - 1,000 mV ranges: [-1,000 to 0], [-500 to 500], [0 to 1,000]
  - 1,500 mV range: [-500 to 1,000]
  - 2,000 mV ranges: [-1,000 to 1,000], [-2,000 to 2,000]
  - **3,000 mV extreme**: [-3,000 to 3,000]

**Use cases**:
- Negative ranges: Reducing conditions, anaerobic environments
- Balanced ranges: Water treatment, aquaculture
- Positive ranges: Oxidizing conditions, disinfection monitoring
- Extreme: Electrochemical processes, industrial applications

### Temperature (°C)
- **Presets**:
  - Precision: 10°C ranges [15-25], [20-30]
  - Standard: 25°C range [0-25]
  - Extended: 50°C ranges [0-50], [-10 to 40]
  - Full water: 100°C range [0-100]
  - Industrial: 140°C range [-20 to 120]

**Use cases**:
- Narrow ranges: Room temperature monitoring, climate control
- Standard ranges: Environmental water, aquariums, pools
- Extended ranges: Industrial processes, outdoor monitoring
- Industrial: Steam, heating systems, cryogenic applications

## Settings

### Auto-Scaling Toggle
- **Enabled (default)**: Charts automatically adjust to fit data using presets
- **Disabled**: Charts use fixed maximum ranges (manual mode)

### Manual Override
When auto-scaling is disabled, charts use these fixed ranges:
- pH: 0-14
- Conductivity: 0-10,000 µS/cm
- Redox: -2,000 to 2,000 mV
- Temperature: 0-50°C

## Technical Details

### Selection Algorithm
```
1. Get min/max values from visible data (last 10 minutes)
2. Add 10% buffer: 
   bufferedMin = min - (max - min) * 0.1
   bufferedMax = max + (max - min) * 0.1
3. Find smallest preset where:
   preset.min <= bufferedMin AND preset.max >= bufferedMax
4. If no preset fits, use maximum range for that metric
```

### Hysteresis
To prevent flickering between scales:
- Scale only changes if data exceeds current range by >5%
- Or if data fits in a range >20% smaller for >30 seconds

### Grid Line Calculation
Each preset has predefined tick intervals to ensure clean numbers:
- pH: ticks every 0.5 or 1 or 2 pH units
- Conductivity: scaled to range (20, 200, 2,000, etc.)
- Redox: every 50, 100, 200, or 500 mV
- Temperature: every 5 or 10°C

## Examples

### Example 1: pH Titration
**Data range**: 6.8 - 7.4 pH
- Buffer: 6.74 - 7.46 pH
- Selected preset: **6-8 pH** (2 pH range)
- Grid: 6.0, 6.5, 7.0, 7.5, 8.0

### Example 2: Conductivity Monitoring
**Data range**: 450 - 520 µS/cm
- Buffer: 423 - 547 µS/cm
- Selected preset: **0-1,000 µS/cm**
- Grid: 0, 200, 400, 600, 800, 1,000

### Example 3: Redox in Reducing Environment
**Data range**: -180 to -95 mV
- Buffer: -188.5 to -86.5 mV
- Selected preset: **-200 to 0 mV**
- Grid: -200, -150, -100, -50, 0

## Troubleshooting

**Q: Chart scale keeps changing**
- Data is near a scale boundary. Enable a larger fixed scale or adjust your measurement process.

**Q: Data points are clipped at top/bottom**
- Rare edge case where data exceeds maximum preset. Check sensor calibration.

**Q: Grid lines have awkward numbers**
- Should not happen with presets. Report as bug if occurs.

**Q: Want to lock scale manually**
- Disable auto-scaling in Settings and chart will use fixed range.

## Future Enhancements

- [ ] Per-chart manual scale override
- [ ] Custom preset creation
- [ ] Scale lock button on chart UI
- [ ] Historical scale preferences saved per session
