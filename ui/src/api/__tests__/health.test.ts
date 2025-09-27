import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { streamHealthLogsNdjson } from '../health';

const encoder = new TextEncoder();

const createNdjsonResponse = (lines: string[]): Response => {
  const stream = new ReadableStream({
    start(controller) {
      for (const line of lines) {
        controller.enqueue(encoder.encode(`${line}\n`));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: {
      'Content-Type': 'application/x-ndjson',
    },
  });
};

describe('streamHealthLogsNdjson', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns a reader that streams NDJSON chunks', async () => {
    const fetchMock = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(createNdjsonResponse(['{"id":1}', '{"id":2}']));

    const reader = await streamHealthLogsNdjson({ limit: 2 });
    const first = await reader.read();
    expect(first.done).toBe(false);
    expect(first.value).toContain('{"id":1}');

    const second = await reader.read();
    expect(second.done).toBe(false);
    expect(second.value).toContain('{"id":2}');

    const third = await reader.read();
    expect(third.done).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/health/logs.ndjson?'), expect.any(Object));
  });

  it('appends filter parameters to the request', async () => {
    const fetchMock = vi
      .spyOn(global, 'fetch')
      .mockResolvedValue(createNdjsonResponse([]));

    const reader = await streamHealthLogsNdjson({ limit: 5, level: 'warning', category: 'capture' });
    const result = await reader.read();
    expect(result.done).toBe(true);

    const requestUrl = (fetchMock.mock.calls[0]?.[0] as string) ?? '';
    expect(requestUrl).toContain('level=warning');
    expect(requestUrl).toContain('category=capture');
  });
});
