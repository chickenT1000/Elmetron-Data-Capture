import { useState, type ReactNode } from 'react';
import { STORAGE_KEY, SettingsContext, DEFAULT_SETTINGS, sanitizeOperatorName, type AppSettings } from './settings';

export const SettingsProvider = ({ children }: { children: ReactNode }) => {
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Merge with defaults to ensure new fields exist
        const sanitized = {
          ...DEFAULT_SETTINGS,
          ...parsed,
          operatorName: sanitizeOperatorName(parsed.operatorName || DEFAULT_SETTINGS.operatorName),
          autoscalingMode: parsed.autoscalingMode || DEFAULT_SETTINGS.autoscalingMode,
          customRanges: parsed.customRanges ? {
            ...DEFAULT_SETTINGS.customRanges,
            ...parsed.customRanges,
          } : DEFAULT_SETTINGS.customRanges,
        };
        return sanitized;
      }
    } catch (error) {
      console.error('Failed to load app settings:', error);
    }
    return DEFAULT_SETTINGS;
  });

  const updateSettings = (newSettings: AppSettings) => {
    // Sanitize operator name before saving
    const sanitized = {
      ...newSettings,
      operatorName: sanitizeOperatorName(newSettings.operatorName),
    };

    setSettings(sanitized);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized));
    } catch (error) {
      console.error('Failed to save app settings:', error);
    }
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  );
};
