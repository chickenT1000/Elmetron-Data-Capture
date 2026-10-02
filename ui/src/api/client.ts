export async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  return result as T;
}

export function installApiFetch(): void {
  const original = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, window.location.href);
    const method = (init?.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    if (url.origin === window.location.origin && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const cookie = document.cookie.split('; ').find(c => c.startsWith('elmetron_csrf='));
      const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined));
      if (cookie) headers.set('X-Elmetron-CSRF', decodeURIComponent(cookie.split('=').slice(1).join('=')));
      init = { ...init, headers };
    }
    return original(input, init);
  };
}
