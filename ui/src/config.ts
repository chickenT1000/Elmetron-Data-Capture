const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8050';
const DEFAULT_HEALTH_BASE_URL = 'http://127.0.0.1:8051';

const normalizeBaseUrl = (value: string | undefined, fallback: string): string => {
  if (!value || !value.trim()) {
    return fallback;
  }
  return value.replace(/\/+$/, '');
};

export const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL as string | undefined,
  DEFAULT_API_BASE_URL,
);

export const HEALTH_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_HEALTH_BASE_URL as string | undefined,
  DEFAULT_HEALTH_BASE_URL,
);

const buildUrl = (baseUrl: string, path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
};

export const buildApiUrl = (path: string): string => buildUrl(API_BASE_URL, path);

export const buildHealthUrl = (path: string): string => buildUrl(HEALTH_BASE_URL, path);
