import { createContext, useContext } from 'react';
export const STORAGE_KEY = 'appSettings';

// Operator name validation rules
const OPERATOR_NAME_MAX_LENGTH = 50;
const OPERATOR_NAME_MIN_LENGTH = 1;
const OPERATOR_NAME_ALLOWED_PATTERN = /^[\p{L}\p{N}\s\-_.]+$/u; // Alphanumeric, spaces, hyphens, underscores, periods

export type AutoscalingMode = 'presets' | 'dynamic' | 'fixed';

export interface CustomRanges {
  ph: { min: number; max: number };
  conductivity: { min: number; max: number };
  redox: { min: number; max: number };
  temperature: { min: number; max: number };
}

export interface AppSettings {
  gapThresholdSeconds: number;
  autoScalingEnabled: boolean;
  autoscalingMode: AutoscalingMode;
  customRanges: CustomRanges;
  operatorName: string;
}

export const DEFAULT_SETTINGS: AppSettings = {
  gapThresholdSeconds: 15,
  autoScalingEnabled: true,
  autoscalingMode: 'presets',
  customRanges: {
    ph: { min: 0, max: 14 },
    conductivity: { min: 0, max: 10000 },
    redox: { min: -2000, max: 2000 },
    temperature: { min: 0, max: 50 },
  },
  operatorName: '',
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
  sanitized = sanitized.replace(/[^\p{L}\p{N}\s\-_.]/gu, '');

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
    return null;
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

export const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return context;
};
