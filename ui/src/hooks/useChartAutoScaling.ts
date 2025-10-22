import { useMemo } from 'react';
import type { MeasurementDataPoint } from './useRecentMeasurements';

export interface ScalePreset {
  min: number;
  max: number;
  ticks: number[];
  label: string;
}

export type MetricType = 'ph' | 'redox' | 'conductivity' | 'temperature';

// Define preset ranges for each metric type
const SCALE_PRESETS: Record<MetricType, ScalePreset[]> = {
  ph: [
    // 1 pH ranges (minimum delta) - minimum 5 ticks for good grid coverage
    { min: 0, max: 1, ticks: [0, 0.25, 0.5, 0.75, 1], label: '0-1 pH' },
    { min: 1, max: 2, ticks: [1, 1.25, 1.5, 1.75, 2], label: '1-2 pH' },
    { min: 2, max: 3, ticks: [2, 2.25, 2.5, 2.75, 3], label: '2-3 pH' },
    { min: 3, max: 4, ticks: [3, 3.25, 3.5, 3.75, 4], label: '3-4 pH' },
    { min: 4, max: 5, ticks: [4, 4.25, 4.5, 4.75, 5], label: '4-5 pH' },
    { min: 5, max: 6, ticks: [5, 5.25, 5.5, 5.75, 6], label: '5-6 pH' },
    { min: 6, max: 7, ticks: [6, 6.25, 6.5, 6.75, 7], label: '6-7 pH' },
    { min: 7, max: 8, ticks: [7, 7.25, 7.5, 7.75, 8], label: '7-8 pH' },
    { min: 8, max: 9, ticks: [8, 8.25, 8.5, 8.75, 9], label: '8-9 pH' },
    { min: 9, max: 10, ticks: [9, 9.25, 9.5, 9.75, 10], label: '9-10 pH' },
    { min: 10, max: 11, ticks: [10, 10.25, 10.5, 10.75, 11], label: '10-11 pH' },
    { min: 11, max: 12, ticks: [11, 11.25, 11.5, 11.75, 12], label: '11-12 pH' },
    { min: 12, max: 13, ticks: [12, 12.25, 12.5, 12.75, 13], label: '12-13 pH' },
    { min: 13, max: 14, ticks: [13, 13.25, 13.5, 13.75, 14], label: '13-14 pH' },
    // 2 pH ranges
    { min: 0, max: 2, ticks: [0, 0.5, 1, 1.5, 2], label: '0-2 pH' },
    { min: 2, max: 4, ticks: [2, 2.5, 3, 3.5, 4], label: '2-4 pH' },
    { min: 4, max: 6, ticks: [4, 4.5, 5, 5.5, 6], label: '4-6 pH' },
    { min: 6, max: 8, ticks: [6, 6.5, 7, 7.5, 8], label: '6-8 pH' },
    { min: 8, max: 10, ticks: [8, 8.5, 9, 9.5, 10], label: '8-10 pH' },
    { min: 10, max: 12, ticks: [10, 10.5, 11, 11.5, 12], label: '10-12 pH' },
    { min: 12, max: 14, ticks: [12, 12.5, 13, 13.5, 14], label: '12-14 pH' },
    // 4 pH ranges
    { min: 0, max: 4, ticks: [0, 1, 2, 3, 4], label: '0-4 pH' },
    { min: 4, max: 8, ticks: [4, 5, 6, 7, 8], label: '4-8 pH' },
    { min: 8, max: 12, ticks: [8, 9, 10, 11, 12], label: '8-12 pH' },
    { min: 12, max: 16, ticks: [12, 13, 14, 15, 16], label: '12-16 pH' },
    // 7 pH ranges
    { min: 0, max: 7, ticks: [0, 1, 2, 3, 4, 5, 6], label: '0-7 pH' },
    { min: 3.5, max: 10.5, ticks: [3.5, 5, 6.5, 8, 9.5, 10.5], label: '3.5-10.5 pH' },
    { min: 7, max: 14, ticks: [7, 9, 11, 13], label: '7-14 pH' },
    // Full standard range
    { min: 0, max: 14, ticks: [0, 2, 4, 6, 8, 10, 12], label: '0-14 pH' },
    // Extended range
    { min: -4, max: 20, ticks: [-4, 0, 4, 8, 12, 16], label: '-4 to 20 pH (full)' },
  ],

  conductivity: [
    // Ultra-pure water
    { min: 0, max: 10, ticks: [0, 2, 4, 6, 8, 10], label: '0-10 µS/cm' },
    { min: 0, max: 20, ticks: [0, 5, 10, 15, 20], label: '0-20 µS/cm' },
    { min: 0, max: 50, ticks: [0, 10, 20, 30, 40, 50], label: '0-50 µS/cm' },
    // Pure/distilled
    { min: 0, max: 100, ticks: [0, 20, 40, 60, 80, 100], label: '0-100 µS/cm' },
    { min: 0, max: 200, ticks: [0, 50, 100, 150, 200], label: '0-200 µS/cm' },
    { min: 0, max: 500, ticks: [0, 100, 200, 300, 400, 500], label: '0-500 µS/cm' },
    // Drinking water
    { min: 0, max: 1000, ticks: [0, 200, 400, 600, 800, 1000], label: '0-1,000 µS/cm' },
    { min: 0, max: 2000, ticks: [0, 500, 1000, 1500, 2000], label: '0-2,000 µS/cm' },
    // General water
    { min: 0, max: 5000, ticks: [0, 1000, 2000, 3000, 4000, 5000], label: '0-5,000 µS/cm' },
    { min: 0, max: 10000, ticks: [0, 2000, 4000, 6000, 8000, 10000], label: '0-10,000 µS/cm' },
    // High conductivity
    { min: 0, max: 20000, ticks: [0, 5000, 10000, 15000, 20000], label: '0-20,000 µS/cm' },
    { min: 0, max: 50000, ticks: [0, 10000, 20000, 30000, 40000, 50000], label: '0-50,000 µS/cm' },
    { min: 0, max: 100000, ticks: [0, 20000, 40000, 60000, 80000, 100000], label: '0-100,000 µS/cm' },
    // Seawater
    { min: 0, max: 200000, ticks: [0, 50000, 100000, 150000, 200000], label: '0-200,000 µS/cm' },
    // Extreme (industrial/brine)
    { min: 0, max: 500000, ticks: [0, 100000, 200000, 300000, 400000, 500000], label: '0-500,000 µS/cm' },
  ],

  redox: [
    // 200 mV ranges
    { min: -200, max: 0, ticks: [-200, -150, -100, -50, 0], label: '-200 to 0 mV' },
    { min: -100, max: 100, ticks: [-100, -50, 0, 50, 100], label: '-100 to 100 mV' },
    { min: 0, max: 200, ticks: [0, 50, 100, 150, 200], label: '0 to 200 mV' },
    // 500 mV ranges
    { min: -500, max: 0, ticks: [-500, -400, -300, -200, -100, 0], label: '-500 to 0 mV' },
    { min: -250, max: 250, ticks: [-250, -150, -50, 50, 150, 250], label: '-250 to 250 mV' },
    { min: 0, max: 500, ticks: [0, 100, 200, 300, 400, 500], label: '0 to 500 mV' },
    // 1,000 mV ranges
    { min: -1000, max: 0, ticks: [-1000, -800, -600, -400, -200, 0], label: '-1,000 to 0 mV' },
    { min: -500, max: 500, ticks: [-500, -300, -100, 100, 300, 500], label: '-500 to 500 mV' },
    { min: 0, max: 1000, ticks: [0, 200, 400, 600, 800, 1000], label: '0 to 1,000 mV' },
    // 1,500 mV range
    { min: -500, max: 1000, ticks: [-500, -200, 100, 400, 700, 1000], label: '-500 to 1,000 mV' },
    // 2,000 mV ranges
    { min: -1000, max: 1000, ticks: [-1000, -600, -200, 200, 600, 1000], label: '-1,000 to 1,000 mV' },
    { min: -2000, max: 2000, ticks: [-2000, -1200, -400, 400, 1200, 2000], label: '-2,000 to 2,000 mV' },
    // 3,000 mV extreme
    { min: -3000, max: 3000, ticks: [-3000, -1800, -600, 600, 1800, 3000], label: '-3,000 to 3,000 mV' },
  ],

  temperature: [
    // Precision ranges - max 6 ticks with even spacing
    { min: 15, max: 25, ticks: [15, 17, 19, 21, 23, 25], label: '15-25 °C' },
    { min: 20, max: 30, ticks: [20, 22, 24, 26, 28, 30], label: '20-30 °C' },
    // Standard ranges
    { min: 0, max: 25, ticks: [0, 5, 10, 15, 20, 25], label: '0-25 °C' },
    { min: 0, max: 50, ticks: [0, 10, 20, 30, 40, 50], label: '0-50 °C' },
    { min: -10, max: 40, ticks: [-10, 0, 10, 20, 30, 40], label: '-10 to 40 °C' },
    // Extended ranges
    { min: 0, max: 100, ticks: [0, 20, 40, 60, 80, 100], label: '0-100 °C' },
    // Industrial
    { min: -20, max: 120, ticks: [-20, 10, 40, 70, 100], label: '-20 to 120 °C' },
  ],
};

// Default fixed scales (when auto-scaling is disabled)
const DEFAULT_FIXED_SCALES: Record<MetricType, ScalePreset> = {
  ph: { min: 0, max: 14, ticks: [0, 2, 4, 6, 8, 10, 12, 14], label: '0-14 pH (fixed)' },
  conductivity: { min: 0, max: 10000, ticks: [0, 2000, 4000, 6000, 8000, 10000], label: '0-10,000 µS/cm (fixed)' },
  redox: { min: -2000, max: 2000, ticks: [-2000, -1500, -1000, -500, 0, 500, 1000, 1500, 2000], label: '-2,000 to 2,000 mV (fixed)' },
  temperature: { min: 0, max: 50, ticks: [0, 10, 20, 30, 40, 50], label: '0-50 °C (fixed)' },
};

interface UseChartAutoScalingOptions {
  data: MeasurementDataPoint[];
  dataKey: 'ph' | 'redox' | 'conductivity' | 'temperature';
  enabled?: boolean;
  bufferPercent?: number; // Default 10%
}

interface ChartScaleResult {
  domain: [number, number];
  ticks: number[];
  preset: ScalePreset;
}

/**
 * Hook for automatic chart Y-axis scaling with preset ranges
 * 
 * @param options Configuration options
 * @returns Optimal scale configuration with domain and ticks
 */
export function useChartAutoScaling({
  data,
  dataKey,
  enabled = true,
  bufferPercent = 0.10,
}: UseChartAutoScalingOptions): ChartScaleResult {
  return useMemo(() => {
    // If auto-scaling is disabled, return fixed scale
    if (!enabled) {
      const fixedScale = DEFAULT_FIXED_SCALES[dataKey];
      return {
        domain: [fixedScale.min, fixedScale.max] as [number, number],
        ticks: fixedScale.ticks,
        preset: fixedScale,
      };
    }

    // Filter data to only include valid values for this metric
    const validData = data
      .map(d => d[dataKey])
      .filter((val): val is number => val !== null && val !== undefined && !isNaN(val));

    // If no data, return default preset for this metric type
    if (validData.length === 0) {
      const defaultPreset = SCALE_PRESETS[dataKey][Math.floor(SCALE_PRESETS[dataKey].length / 2)];
      return {
        domain: [defaultPreset.min, defaultPreset.max] as [number, number],
        ticks: defaultPreset.ticks,
        preset: defaultPreset,
      };
    }

    // Find min/max values in data
    const dataMin = Math.min(...validData);
    const dataMax = Math.max(...validData);

    // Add buffer to avoid data touching edges
    const range = dataMax - dataMin;
    const buffer = range * bufferPercent;
    const bufferedMin = dataMin - buffer;
    const bufferedMax = dataMax + buffer;

    // Find the smallest preset that fits the buffered data
    const presets = SCALE_PRESETS[dataKey];
    let selectedPreset = presets[presets.length - 1]; // Default to largest

    for (const preset of presets) {
      if (preset.min <= bufferedMin && preset.max >= bufferedMax) {
        selectedPreset = preset;
        break;
      }
    }

    return {
      domain: [selectedPreset.min, selectedPreset.max] as [number, number],
      ticks: selectedPreset.ticks,
      preset: selectedPreset,
    };
  }, [data, dataKey, enabled, bufferPercent]);
}
