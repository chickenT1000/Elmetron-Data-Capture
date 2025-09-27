const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8050';

const normalizeBaseUrl = (value?: string): string => {
  if (!value || !value.trim()) {
    return DEFAULT_API_BASE_URL;
  }
  return value.replace(/\/+$/, '');
};

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL as string | undefined);

export const buildApiUrl = (path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};
