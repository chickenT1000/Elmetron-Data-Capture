import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

const STORAGE_KEY = 'appSettings';

// Operator name validation rules
const OPERATOR_NAME_MAX_LENGTH = 50;
const OPERATOR_NAME_MIN_LENGTH = 1;
const OPERATOR_NAME_ALLOWED_PATTERN = /^[a-zA-Z0-9\s\-_.]+$/; // Alphanumeric, spaces, hyphens, underscores, periods

export interface AppSettings {
  gapThresholdSeconds: number;
  autoScalingEnabled: boolean;
  operatorName: string;
}

export const DEFAULT_SETTINGS: AppSettings = {
  gapThresholdSeconds: 15,
  autoScalingEnabled: true,
  operatorName: 'User',
};

/**
 * Sanitize and validate operator name
 * - Trims whitespace
 * - Enforces length limits
 * - Allows only safe characters (alphanumeric, spaces, -, _, .)
 * - Returns sanitized string or default if invalid
 */
export const sanitizeOperatorName = (name: string): string => {
  if (!name || typeof name !== 'string') {
    return DEFAULT_SETTINGS.operatorName;
  }

  // Trim whitespace
  let sanitized = name.trim();

  // Check length
  if (sanitized.length < OPERATOR_NAME_MIN_LENGTH) {
    return DEFAULT_SETTINGS.operatorName;
  }

  if (sanitized.length > OPERATOR_NAME_MAX_LENGTH) {
    sanitized = sanitized.substring(0, OPERATOR_NAME_MAX_LENGTH);
  }

  // Remove any characters that don't match the allowed pattern
  sanitized = sanitized.replace(/[^a-zA-Z0-9\s\-_.]/g, '');

  // If nothing left after sanitization, return default
  if (sanitized.length < OPERATOR_NAME_MIN_LENGTH) {
    return DEFAULT_SETTINGS.operatorName;
  }

  return sanitized;
};

/**
 * Validate operator name and return error message if invalid
 */
export const validateOperatorName = (name: string): string | null => {
  if (!name || name.trim().length === 0) {
    return 'Operator name cannot be empty';
  }

  const trimmed = name.trim();

  if (trimmed.length < OPERATOR_NAME_MIN_LENGTH) {
    return 'Operator name is too short';
  }

  if (trimmed.length > OPERATOR_NAME_MAX_LENGTH) {
    return `Operator name cannot exceed ${OPERATOR_NAME_MAX_LENGTH} characters`;
  }

  if (!OPERATOR_NAME_ALLOWED_PATTERN.test(trimmed)) {
    return 'Only letters, numbers, spaces, hyphens, underscores, and periods are allowed';
  }

  return null; // Valid
};

interface SettingsContextType {
  settings: AppSettings;
  updateSettings: (newSettings: AppSettings) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider = ({ children }: { children: ReactNode }) => {
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Sanitize operator name on load
        const sanitized = {
          ...DEFAULT_SETTINGS,
          ...parsed,
          operatorName: sanitizeOperatorName(parsed.operatorName || DEFAULT_SETTINGS.operatorName),
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

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return context;
};
