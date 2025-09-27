import { buildApiUrl } from '../config';

export interface SessionSummary {
  id: number;
  started_at: string;
  ended_at: string | null;
  note?: string | null;
  instrument?: {
    serial?: string | null;
    description?: string | null;
    model?: string | null;
  } | null;
  counts?: {
    measurements?: number;
    frames?: number;
    audit_events?: number;
  } | null;
  metadata?: Record<string, unknown> | null;
  latest_measurement_at?: string | null;
}

export interface SessionEvaluationPoint {
  measurement_id: number;
  frame_id: number;
  timestamp: string | null;
  captured_at: string | null;
  offset_seconds: number | null;
  value: number | null;
  unit: string | null;
  temperature: number | null;
  temperature_unit: string | null;
  payload?: Record<string, unknown>;
  analytics?: Record<string, unknown>;
}

export interface SessionEvaluationStatistics {
  min: number | null;
  max: number | null;
  average: number | null;
  samples: number;
  unit: string | null;
}

export interface SessionEvaluationMarker {
  type: string;
  timestamp: string | null;
  offset_seconds: number | null;
  measurement_id: number | null;
}

export interface SessionEvaluationResponse {
  session: SessionSummary;
  anchor: string;
  anchor_timestamp: string | null;
  series: SessionEvaluationPoint[];
  markers: SessionEvaluationMarker[];
  statistics: {
    value: SessionEvaluationStatistics;
    temperature: SessionEvaluationStatistics;
  };
  duration_seconds: number | null;
  samples: number;
}

export async function fetchRecentSessions({
  limit = 10,
}: { limit?: number } = {}): Promise<SessionSummary[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(buildApiUrl(`/sessions/recent?${params.toString()}`), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    const error: Error & { status?: number } = new Error(
      `Session list request failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  const payload = (await response.json()) as { sessions?: SessionSummary[] };
  return payload.sessions ?? [];
}

export async function fetchSessionEvaluation(
  sessionId: number,
  { anchor = 'start' }: { anchor?: string } = {},
): Promise<SessionEvaluationResponse> {
  const params = new URLSearchParams();
  if (anchor) {
    params.set('anchor', anchor);
  }
  const query = params.toString();
  const url = buildApiUrl(`/sessions/${sessionId}/evaluation${query ? `?${query}` : ''}`);
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    const error: Error & { status?: number } = new Error(
      `Session evaluation request failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return (await response.json()) as SessionEvaluationResponse;
}

export async function downloadSessionEvaluationJson(
  sessionId: number,
  { anchor = 'start', filename }: { anchor?: string; filename?: string } = {},
): Promise<Blob> {
  const params = new URLSearchParams({ format: 'json' });
  if (anchor) {
    params.set('anchor', anchor);
  }
  if (filename) {
    params.set('filename', filename);
  }
  const response = await fetch(
    buildApiUrl(`/sessions/${sessionId}/evaluation/export?${params.toString()}`),
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    },
  );
  if (!response.ok) {
    const error: Error & { status?: number } = new Error(
      `Session evaluation export failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return await response.blob();
}
