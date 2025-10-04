import { useState, useEffect } from 'react';

const STORAGE_KEY = 'chartSettings';

interface ChartSettings {
  gapThresholdSeconds: number;
  autoScalingEnabled: boolean;
}

const DEFAULT_SETTINGS: ChartSettings = {
  gapThresholdSeconds: 15,
  autoScalingEnabled: true,
};

/**
 * Custom hook for managing chart display settings with localStorage persistence
 * 
 * Settings:
 * - gapThresholdSeconds: Maximum time gap (1-60 seconds) to connect measurement points
 *   Points separated by more than this will show as disconnected lines
 * - autoScalingEnabled: Enable/disable automatic Y-axis scaling with preset ranges
 */
export const useChartSettings = () => {
  const [settings, setSettings] = useState<ChartSettings>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return { ...DEFAULT_SETTINGS, ...parsed };
      }
    } catch (error) {
      console.error('Failed to load chart settings:', error);
    }
    return DEFAULT_SETTINGS;
  });

  // Save to localStorage whenever settings change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to save chart settings:', error);
    }
  }, [settings]);

  const updateGapThreshold = (seconds: number) => {
    // Clamp value between 1 and 60 seconds
    const clamped = Math.min(60, Math.max(1, seconds));
    setSettings(prev => ({ ...prev, gapThresholdSeconds: clamped }));
  };

  const toggleAutoScaling = (enabled: boolean) => {
    setSettings(prev => ({ ...prev, autoScalingEnabled: enabled }));
  };

  const resetToDefaults = () => {
    setSettings(DEFAULT_SETTINGS);
  };

  return {
    settings,
    updateGapThreshold,
    toggleAutoScaling,
    resetToDefaults,
  };
};
