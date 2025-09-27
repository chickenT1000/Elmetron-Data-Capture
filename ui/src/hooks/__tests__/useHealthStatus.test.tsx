import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useHealthStatus } from '../useHealthStatus';

const createWrapper = () => {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const Provider = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return Provider;
};

describe('useHealthStatus', () => {
  const sampleResponse = {
    state: 'running',
    frames: 123,
    bytes_read: 4567,
    last_frame_at: '2025-09-27T10:00:00Z',
    last_window_started: '2025-09-27T09:59:00Z',
    command_metrics: {
      queue_depth: 3,
      inflight: 1,
      history: [
        {
          timestamp: 1000,
          timestamp_iso: '2025-09-27T09:59:00Z',
          queue_depth: 2,
          inflight: 1,
        },
        {
          timestamp: 2000,
          timestamp_iso: '2025-09-27T09:59:30Z',
          queue_depth: 3,
          inflight: 2,
        },
      ],
    },
    analytics_profile: {
      frames_processed: 10,
      throttled_frames: 2,
      average_processing_time_ms: 12.5,
      max_processing_time_ms: 40,
      current_rate_per_minute: 55.5,
    },
    response_times: {
      last_ms: 30,
      average_ms: 25,
      max_ms: 80,
      samples: 4,
    },
  };

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(sampleResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('maps analytics profile and command history from the health response', async () => {
    const { result } = renderHook(() => useHealthStatus(60000), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.analyticsProfile?.frames_processed).toBe(10);
    expect(result.current.commandHistory).toHaveLength(2);
    expect(result.current.commandHistory?.[0]?.timestamp).toBe(1000);
    expect(result.current.responseTimes?.average_ms).toBe(25);
  });
});
