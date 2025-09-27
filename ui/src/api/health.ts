import { buildApiUrl } from '../config';
import JSZip from 'jszip';

export interface LogRotationStatus {
  name?: string;
  status?: string;
  message?: string;
  within_threshold?: boolean | null;
  last_run_time?: string | null;
  next_run_time?: string | null;
  last_run_age_minutes?: number | null;
  threshold_minutes?: number | null;
  last_task_result?: number | null;
  last_task_result_raw?: unknown;
}

export interface HealthWatchdogEvent {
  kind: string;
  message: string;
  occurred_at: string;
  payload?: Record<string, unknown> | null;
}

export interface CommandScheduleEntry {
  name: string;
  active: boolean;
  in_flight: boolean;
  runs: number;
  last_error?: string | null;
  next_due_epoch?: number | null;
  next_due_iso?: string | null;
  pending_source?: string | null;
  pending_category?: string | null;
}

export interface CommandMetrics {
  queue_depth?: number | null;
  result_backlog?: number | null;
  inflight?: number;
  scheduled?: CommandScheduleEntry[];
  worker_running?: boolean;
  async_enabled?: boolean;
}

export interface HealthResponse {
  state: string;
  frames: number;
  bytes_read: number;
  last_frame_at: string | null;
  last_window_started: string | null;
  watchdog_alert?: string | null;
  detail?: string | null;
  log_rotation?: LogRotationStatus | null;
  watchdog_history?: HealthWatchdogEvent[] | null;
  command_metrics?: CommandMetrics | null;
}

export const healthQueryKey = ['health-status'] as const;

export async function fetchHealthStatus(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(buildApiUrl('/health'), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    const error: Error & { status?: number } = new Error(
      `Health request failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }

  return (await response.json()) as HealthResponse;
}

export interface HealthLogEvent {
  id: number;
  session_id: number;
  level: string;
  category: string;
  message: string;
  payload?: Record<string, unknown> | null;
  created_at: string;
}

export const healthLogQueryKey = (limit: number) => ['health-log-events', limit] as const;

export async function fetchHealthLogEvents(
  { limit = 20, sinceId }: { limit?: number; sinceId?: number },
  signal?: AbortSignal,
): Promise<HealthLogEvent[]> {
  const params = new URLSearchParams({ limit: String(limit ?? 20) });
  if (sinceId !== undefined && sinceId !== null) {
    params.set('since_id', String(sinceId));
  }

  const response = await fetch(buildApiUrl(`/health/logs?${params.toString()}`), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    const error: Error & { status?: number } = new Error(
      `Health logs request failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }

  const payload = (await response.json()) as { events?: HealthLogEvent[] };
  return payload.events ?? [];
}


export interface DiagnosticBundleOptions {
  events?: number;
  sessions?: number;
}

export interface DiagnosticBundleManifest {
  generated_at?: string;
  tool?: string;
  version?: string;
  counts?: {
    events?: number;
    sessions?: number;
  };
  context?: {
    database_path?: string | null;
    config_available?: boolean;
  };
  files?: Record<string, string>;
}

export interface DiagnosticBundleResult {
  blob: Blob;
  filename: string;
  manifest?: DiagnosticBundleManifest;
}

function resolveFilename(headerValue?: string | null): string {
  if (!headerValue) {
    return 'elmetron_diagnostic_bundle.zip';
  }
  const match = /filename\*?="?([^";]+)"?/i.exec(headerValue);
  if (match && match[1]) {
    return decodeURIComponent(match[1]);
  }
  return 'elmetron_diagnostic_bundle.zip';
}

export async function fetchDiagnosticBundle(
  options: DiagnosticBundleOptions = {},
  signal?: AbortSignal,
): Promise<DiagnosticBundleResult> {
  const params = new URLSearchParams();
  if (options.events !== undefined) {
    params.set('events', String(options.events));
  }
  if (options.sessions !== undefined) {
    params.set('sessions', String(options.sessions));
  }
  const query = params.toString();
  const response = await fetch(
    buildApiUrl(`/health/bundle${query ? `?${query}` : ''}`),
    {
      method: 'GET',
      headers: {
        Accept: 'application/zip',
      },
      signal,
    },
  );

  if (!response.ok) {
    const error: Error & { status?: number } = new Error(
      `Diagnostic bundle request failed with status ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }

  const blob = await response.blob();

  let manifest: DiagnosticBundleManifest | undefined;
  try {
    const zip = await JSZip.loadAsync(blob);
    const manifestEntry = zip.file('manifest.json');
    if (manifestEntry) {
      const manifestText = await manifestEntry.async('string');
      manifest = JSON.parse(manifestText) as DiagnosticBundleManifest;
    }
  } catch (parseError) {
    console.warn('Failed to read diagnostic manifest', parseError);
  }

  const filename = resolveFilename(response.headers.get('Content-Disposition'));
  return { blob, filename, manifest };
}
