import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  downloadSessionEvaluationJson,
  fetchRecentSessions,
  fetchSessionEvaluation,
  type SessionEvaluationResponse,
} from '../sessions';

describe('sessions api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchRecentSessions returns session list payload', async () => {
    const payload = {
      sessions: [
        {
          id: 42,
          started_at: '2025-09-27T10:00:00Z',
          ended_at: null,
          counts: { measurements: 12 },
        },
      ],
    };
    const fetchMock = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );

    const sessions = await fetchRecentSessions({ limit: 5 });
    expect(Array.isArray(sessions)).toBe(true);
    expect(sessions).toHaveLength(1);
    expect(sessions[0]?.id).toBe(42);
    const requestUrl = (fetchMock.mock.calls[0]?.[0] as string) ?? '';
    expect(requestUrl).toContain('limit=5');
  });

  it('fetchSessionEvaluation returns evaluation payload', async () => {
    const payload: SessionEvaluationResponse = {
      session: {
        id: 99,
        started_at: '2025-09-27T10:00:00Z',
        ended_at: null,
      },
      anchor: 'start',
      anchor_timestamp: '2025-09-27T10:00:00Z',
      series: [],
      markers: [],
      statistics: {
        value: { min: null, max: null, average: null, samples: 0, unit: null },
        temperature: { min: null, max: null, average: null, samples: 0, unit: null },
      },
      duration_seconds: null,
      samples: 0,
    };

    const fetchMock = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );

    const evaluation = await fetchSessionEvaluation(99, { anchor: 'calibration' });
    expect(evaluation.session.id).toBe(99);
    const requestUrl = (fetchMock.mock.calls[0]?.[0] as string) ?? '';
    expect(requestUrl).toContain('/sessions/99/evaluation');
    expect(requestUrl).toContain('anchor=calibration');
  });

  it('downloadSessionEvaluationJson retrieves blob response', async () => {
    const blobPayload = { session: { id: 7 } };
    const response = new Response(JSON.stringify(blobPayload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValue(response);

    const blob = await downloadSessionEvaluationJson(7, { anchor: 'start', filename: 'overlay.json' });
    expect(blob).toMatchObject({ type: 'application/json' });
    const text = await blob.text();
    expect(JSON.parse(text).session.id).toBe(7);
    const requestUrl = (fetchMock.mock.calls[0]?.[0] as string) ?? '';
    expect(requestUrl).toContain('/sessions/7/evaluation/export');
    expect(requestUrl).toContain('filename=overlay.json');
  });
});
