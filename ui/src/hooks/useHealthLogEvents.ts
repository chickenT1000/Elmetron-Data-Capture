import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { buildApiUrl } from '../config';
import {
  fetchHealthLogEvents,
  streamHealthLogsNdjson,
  type HealthLogEvent,
} from '../api/health';

const DEFAULT_LIMIT = 25;
const DEFAULT_REFRESH_MS = 5000;
const MIN_RECONNECT_DELAY_MS = 15000;

export type HealthLogConnectionState = 'idle' | 'loading' | 'connecting' | 'streaming' | 'polling' | 'error';

type MergeResult = {
  items: HealthLogEvent[];
  maxId: number | null;
};

const eventSortKey = (event: HealthLogEvent): number => {
  if (typeof event.id === 'number' && Number.isFinite(event.id)) {
    return event.id;
  }
  const parsed = event.created_at ? Date.parse(event.created_at) : Number.NaN;
  return Number.isNaN(parsed) ? 0 : parsed / 1000;
};

const mergeEvents = (
  previous: HealthLogEvent[],
  incoming: HealthLogEvent[],
  limit: number,
  replace: boolean,
): MergeResult => {
  if (replace && incoming.length === 0) {
    return { items: [], maxId: null };
  }
  const combined = replace ? [...incoming] : [...incoming, ...previous];
  if (!combined.length) {
    return { items: [], maxId: null };
  }
  combined.sort((a, b) => eventSortKey(b) - eventSortKey(a));
  const seen = new Set<number>();
  const items: HealthLogEvent[] = [];
  let maxId: number | null = null;
  for (const event of combined) {
    const idValue = typeof event.id === 'number' ? event.id : null;
    if (idValue !== null) {
      if (seen.has(idValue)) {
        continue;
      }
      seen.add(idValue);
      maxId = maxId === null ? idValue : Math.max(maxId, idValue);
    }
    items.push(event);
    if (items.length >= limit) {
      break;
    }
  }
  if (maxId === null) {
    const firstWithId = items.find((entry) => typeof entry.id === 'number');
    maxId = typeof firstWithId?.id === 'number' ? firstWithId.id : null;
  }
  return { items, maxId };
};

export interface UseHealthLogEventsResult {
  data: HealthLogEvent[];
  connectionState: HealthLogConnectionState;
  isLoading: boolean;
  isFetching: boolean;
  isStreaming: boolean;
  isPolling: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  lastEventId: number | null;
}

export interface UseHealthLogEventsOptions {
  limit?: number;
  fallbackMs?: number;
  level?: string;
  category?: string;
}

export const useHealthLogEvents = (
  options: UseHealthLogEventsOptions = {},
): UseHealthLogEventsResult => {
  const { limit = DEFAULT_LIMIT, fallbackMs = DEFAULT_REFRESH_MS, level, category } = options;
  const [events, setEvents] = useState<HealthLogEvent[]>([]);
  const [connectionState, setConnectionState] = useState<HealthLogConnectionState>('idle');
  const [error, setError] = useState<Error | null>(null);

  const eventsRef = useRef<HealthLogEvent[]>([]);
  const lastEventIdRef = useRef<number | null>(null);
  const fallbackMsRef = useRef<number>(fallbackMs);

  useEffect(() => {
    fallbackMsRef.current = fallbackMs;
  }, [fallbackMs]);

  const updateEvents = useCallback(
    (incoming: HealthLogEvent[], replace = false) => {
      setEvents((previous) => {
        const { items, maxId } = mergeEvents(previous, incoming, limit, replace);
        eventsRef.current = items;
        if (replace && incoming.length === 0) {
          lastEventIdRef.current = null;
        } else if (maxId !== null) {
          lastEventIdRef.current =
            lastEventIdRef.current === null ? maxId : Math.max(lastEventIdRef.current, maxId);
        }
        return items;
      });
    },
    [limit],
  );

  const refetch = useCallback(async () => {
    if (eventsRef.current.length === 0) {
      setConnectionState('loading');
    }
    try {
      const snapshot = await fetchHealthLogEvents({ limit, level, category });
      updateEvents(snapshot, true);
      setError(null);
    } catch (err) {
      const nextError = err instanceof Error ? err : new Error('Failed to fetch log events');
      setError(nextError);
      setConnectionState('error');
    }
  }, [category, level, limit, updateEvents]);

  useEffect(() => {
    let cancelled = false;
    let eventSource: EventSource | null = null;
    let pollTimer: number | null = null;
    let reconnectTimer: number | null = null;
    let ndjsonReader: ReadableStreamDefaultReader<string> | null = null;

    const cleanupSource = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    };

    const clearPolling = () => {
      if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const clearReconnect = () => {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const startPolling = () => {
      clearPolling();
      if (!cancelled) {
        setConnectionState('polling');
      }
      const poll = async () => {
        try {
          const since = lastEventIdRef.current;
          const payload = await fetchHealthLogEvents({
            limit,
            sinceId: since ?? undefined,
            level,
            category,
          });
          if (!cancelled && payload.length) {
            updateEvents(payload);
          }
        } catch (err) {
          if (!cancelled) {
            const nextError = err instanceof Error ? err : new Error('Failed to poll log events');
            setError(nextError);
            setConnectionState('error');
          }
        }
      };
      void poll();
      pollTimer = window.setInterval(poll, Math.max(fallbackMsRef.current, 1000));
    };

    const scheduleReconnect = () => {
      if (reconnectTimer !== null || cancelled) {
        return;
      }
      const delay = Math.max(fallbackMsRef.current, MIN_RECONNECT_DELAY_MS);
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        connectStream();
      }, delay);
    };

    const connectStream = () => {
      if (cancelled) {
        return;
      }
      if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
        startPolling();
        return;
      }
      clearPolling();
      cleanupSource();
      setConnectionState(eventsRef.current.length ? 'connecting' : 'loading');
      setError(null);
      const params = new URLSearchParams({ limit: String(limit) });
      if (lastEventIdRef.current !== null) {
        params.set('since_id', String(lastEventIdRef.current));
      }
      if (level) {
        params.set('level', level);
      }
      if (category) {
        params.set('category', category);
      }
      const streamUrl = `${buildApiUrl('/health/logs/stream')}?${params.toString()}`;
      const source = new window.EventSource(streamUrl);
      eventSource = source;

      const handleMessage = (event: MessageEvent) => {
        if (cancelled || !event.data) {
          return;
        }
        try {
          const payload = JSON.parse(event.data) as HealthLogEvent;
          updateEvents([payload]);
        } catch {
          // ignore malformed payloads
        }
      };

      source.addEventListener('log', handleMessage as EventListener);
      source.onmessage = handleMessage;
      source.onopen = () => {
        if (cancelled) {
          source.close();
          return;
        }
        setConnectionState('streaming');
        clearPolling();
      };
      source.onerror = () => {
        source.removeEventListener('log', handleMessage as EventListener);
        source.close();
        if (cancelled) {
          return;
        }
        eventSource = null;
        setError(new Error('Log stream connection lost'));
        setConnectionState('error');
        startPolling();
        scheduleReconnect();
      };
    };

    const initialise = async () => {
      setConnectionState('loading');
      setError(null);
      try {
        const initial = await fetchHealthLogEvents({ limit, sinceId: undefined, level, category });
        if (!cancelled) {
          updateEvents(initial, true);
        }
      } catch (err) {
        if (!cancelled) {
          const nextError = err instanceof Error ? err : new Error('Failed to load log events');
          setError(nextError);
          setConnectionState('error');
          startPolling();
          scheduleReconnect();
          return;
        }
      }
      if (!cancelled && typeof window !== 'undefined' && typeof window.EventSource === 'function') {
        connectStream();
      } else if (!cancelled) {
        // fallback to NDJSON stream
        setConnectionState('connecting');
        (async () => {
          while (!cancelled) {
            try {
              ndjsonReader = await streamHealthLogsNdjson({ limit, level, category });
              setConnectionState('streaming');
              let buffer = '';
              while (!cancelled && ndjsonReader) {
                const { value, done } = await ndjsonReader.read();
                if (done) break;
                if (value) {
                  buffer += value;
                  const lines = buffer.split('\n');
                  buffer = lines.pop() ?? '';
                  const parsed: HealthLogEvent[] = [];
                  for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                      parsed.push(JSON.parse(line) as HealthLogEvent);
                    } catch (parseErr) {
                      console.warn('Failed to parse NDJSON line', parseErr);
                    }
                  }
                  if (parsed.length) {
                    updateEvents(parsed);
                  }
                }
              }
        } catch (streamErr) {
              if (!cancelled) {
                setError(streamErr instanceof Error ? streamErr : new Error('NDJSON stream error'));
                setConnectionState('error');
                await new Promise((resolve) => setTimeout(resolve, Math.max(fallbackMsRef.current, 1000)));
              }
            } finally {
              if (ndjsonReader) {
                ndjsonReader.cancel().catch(() => undefined);
                ndjsonReader = null;
              }
            }
          }
        })().catch((err) => console.error('NDJSON stream failed', err));
      }
    };

    initialise();

    return () => {
      cancelled = true;
      clearPolling();
      cleanupSource();
      clearReconnect();
      if (ndjsonReader) {
        ndjsonReader.cancel().catch(() => undefined);
        ndjsonReader = null;
      }
    };
  }, [limit, updateEvents, category, level]);

  const isStreaming = connectionState === 'streaming';
  const isPolling = connectionState === 'polling';
  const isError = connectionState === 'error';
  const isLoading =
    (connectionState === 'idle' || connectionState === 'loading' || connectionState === 'connecting') &&
    events.length === 0;
  const isFetching =
    connectionState === 'loading' ||
    connectionState === 'connecting' ||
    connectionState === 'streaming' ||
    connectionState === 'polling';

  const lastEventId = lastEventIdRef.current;

  return useMemo(
    () => ({
      data: events,
      connectionState,
      isLoading,
      isFetching,
      isStreaming,
      isPolling,
      isError,
      error,
      refetch,
      lastEventId,
    }),
    [connectionState, error, events, isError, isFetching, isLoading, isPolling, isStreaming, lastEventId, refetch],
  );
};
