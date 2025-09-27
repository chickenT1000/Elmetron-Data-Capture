import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { useSessionEvaluation } from '../useSessionEvaluation';

const createWrapper = () => {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const Provider = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return Provider;
};

describe('useSessionEvaluation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches evaluation data for the requested session', async () => {
    const payload = {
      session: {
        id: 11,
        started_at: '2025-09-27T10:00:00Z',
        ended_at: null,
      },
      anchor: 'start',
      anchor_timestamp: '2025-09-27T10:00:00Z',
      series: [
        {
          measurement_id: 1,
          frame_id: 1,
          timestamp: '2025-09-27T10:00:00Z',
          captured_at: '2025-09-27T10:00:00Z',
          offset_seconds: 0,
          value: 7.1,
          unit: 'pH',
          temperature: 20,
          temperature_unit: 'C',
        },
      ],
      markers: [],
      statistics: {
        value: { min: 7.1, max: 7.1, average: 7.1, samples: 1, unit: 'pH' },
        temperature: { min: 20, max: 20, average: 20, samples: 1, unit: 'C' },
      },
      duration_seconds: 0,
      samples: 1,
    };

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    const { result } = renderHook(() => useSessionEvaluation(11, 'start'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.session.id).toBe(11);
    expect(result.current.data?.samples).toBe(1);
  });
});
