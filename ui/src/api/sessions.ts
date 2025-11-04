import { buildApiUrl } from '../config';

export async function fetchOperators(): Promise<string[]> {
  const response = await fetch(buildApiUrl('/api/operators'));
  if (!response.ok) {
    throw new Error(`Failed to fetch operators: ${response.status}`);
  }
  const data = await response.json();
  return data.operators || [];
}

export async function updateDefaultOperator(operatorName: string): Promise<void> {
  const response = await fetch(buildApiUrl('/api/config/default-operator'), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ operator_name: operatorName }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to update default operator');
  }
}

export async function updateActiveSessionOperator(operatorName: string): Promise<void> {
  const response = await fetch(buildApiUrl('/api/sessions/active/operator'), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ operator_name: operatorName }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || `Failed to update operator: ${response.status}`);
  }
}

export interface SessionSummary {
  id: number;
  started_at: string;
  ended_at: string | null;
  note?: string | null;
  operator_name?: string | null;
  instrument?: {
    serial?: string | null;
    description?: string | null;
    model?: string | null;
  } | null;
  counts?: {
    measurements?: number;
    ph_measurements?: number;
    redox_measurements?: number;
    conductivity_measurements?: number;
    frames?: number;
    audit_events?: number;
  } | null;
  dominant_parameter?: 'ph' | 'redox' | 'conductivity' | 'none';
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
  marker_number: number;
  offset_seconds: number;
  offset_minutes: number;
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

export interface SessionFilters {
  limit?: number;
  operator?: string;
  start_date?: string;
  end_date?: string;
  has_ph?: boolean;
  has_redox?: boolean;
  has_conductivity?: boolean;
  sort_by?: 'started_at' | 'measurement_count' | 'duration';
  order?: 'asc' | 'desc';
}

export async function fetchRecentSessions(
  filters: SessionFilters = {}
): Promise<SessionSummary[]> {
  const { limit = 10, ...rest } = filters;
  const params = new URLSearchParams({ limit: String(limit) });
  
  // Add optional filters
  if (rest.operator) params.set('operator', rest.operator);
  if (rest.start_date) params.set('start_date', rest.start_date);
  if (rest.end_date) params.set('end_date', rest.end_date);
  if (rest.has_ph !== undefined) params.set('has_ph', String(rest.has_ph));
  if (rest.has_redox !== undefined) params.set('has_redox', String(rest.has_redox));
  if (rest.has_conductivity !== undefined) params.set('has_conductivity', String(rest.has_conductivity));
  if (rest.sort_by) params.set('sort_by', rest.sort_by);
  if (rest.order) params.set('order', rest.order);
  
  const response = await fetch(buildApiUrl(`/api/sessions?${params.toString()}`), {
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
  const url = buildApiUrl(`/api/sessions/${sessionId}/evaluation${query ? `?${query}` : ''}`);
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
    buildApiUrl(`/api/sessions/${sessionId}/export?${params.toString()}`),
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

export async function renameSession(
  sessionId: number,
  name: string
): Promise<{ id: number; name: string; updated_at: string }> {
  const response = await fetch(buildApiUrl(`/api/sessions/${sessionId}/rename`), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: Error & { status?: number } = new Error(
      errorData.error || `Failed to rename session: ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return await response.json();
}

export async function updateSessionOperator(
  sessionId: number,
  operatorName: string | null
): Promise<{ id: number; operator_name: string | null; updated_at: string }> {
  const response = await fetch(buildApiUrl(`/api/sessions/${sessionId}/operator`), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ operator_name: operatorName }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: Error & { status?: number } = new Error(
      errorData.error || `Failed to update operator: ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return await response.json();
}

export async function deleteSession(sessionId: number): Promise<void> {
  const response = await fetch(buildApiUrl(`/api/sessions/${sessionId}`), {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: Error & { status?: number } = new Error(
      errorData.error || `Failed to delete session: ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
}

export interface SessionMarker {
  id: number;
  session_id: number;
  marker_number: number;
  event_timestamp: string;
  offset_seconds: number;
  note?: string;
  created_at: string;
}

export async function fetchSessionMarkers(sessionId: number): Promise<SessionMarker[]> {
  const response = await fetch(buildApiUrl(`/api/sessions/${sessionId}/markers`), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: Error & { status?: number} = new Error(
      errorData.error || `Failed to fetch markers: ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  const data = (await response.json()) as { markers: SessionMarker[] };
  return data.markers;
}

export async function addSessionMarker(
  sessionId: number,
  eventTimestamp: string,
  offsetSeconds: number,
  note?: string
): Promise<SessionMarker> {
  const response = await fetch(buildApiUrl(`/api/sessions/${sessionId}/markers`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      event_timestamp: eventTimestamp,
      offset_seconds: offsetSeconds,
      note: note || '',
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: Error & { status?: number } = new Error(
      errorData.error || `Failed to add marker: ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return (await response.json()) as SessionMarker;
}

export async function deleteSessionMarker(sessionId: number, markerId: number): Promise<void> {
  const response = await fetch(buildApiUrl(`/api/sessions/${sessionId}/markers/${markerId}`), {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: Error & { status?: number } = new Error(
      errorData.error || `Failed to delete marker: ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
}
