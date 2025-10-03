import { Stack, Typography } from '@mui/material';
import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents, type HealthLogConnectionState } from '../hooks/useHealthLogEvents';
import { useLiveStatus } from '../hooks/useLiveStatus';
import { MeasurementPanel } from '../components/MeasurementPanel';
import { CommandHistory } from '../components/CommandHistory';
import { LogFeed } from '../components/LogFeed';
import { RollingChartsPanel } from '../components/RollingChartsPanel';
import type {
  CommandHistoryEntryState,
  DiagnosticLogRowState,
  MeasurementPanelState,
  MetricIndicatorState,
} from '../components/contracts';

const formatNumber = (value?: number | null, digits = 2): string => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return '-';
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
};


const formatDurationMs = (value?: number | null): string => {
  if (!value && value !== 0) return '-';
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`;
  }
  return `${value.toFixed(1)} ms`;
};

const normaliseLogStream = (state: HealthLogConnectionState): 'streaming' | 'polling' | 'idle' => {
  if (state === 'streaming' || state === 'polling') {
    return state;
  }
  return 'idle';
};

const normaliseLogLevel = (level?: string | null): DiagnosticLogRowState['level'] => {
  switch ((level ?? 'info').toLowerCase()) {
    case 'success':
      return 'success';
    case 'warning':
      return 'warning';
    case 'error':
      return 'error';
    default:
      return 'info';
  }
};

export default function DashboardPage() {
  const { data: liveStatus } = useLiveStatus();
  const isArchiveMode = liveStatus?.mode === 'archive';

  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
    commandHistory,
    analyticsProfile,
    responseTimes,
  } = useHealthStatus(2000);

  const logLimit = 25;
  const {
    data: logEvents,
    connectionState,
    isLoading: logsLoading,
    isError: logsError,
    error: logsErrorObj,
  } = useHealthLogEvents({ limit: logLimit, fallbackMs: 5000 });

  const logStream = normaliseLogStream(connectionState);

  const metricCards: MetricIndicatorState[] = [
    {
      id: 'frames',
      label: 'Frames Processed',
      value: formatNumber(health?.frames, 0),
      helperText: `Bytes read ${formatNumber(health?.bytes_read, 0)}`,
      iconToken: 'frames',
    },
    {
      id: 'queue',
      label: 'Command queue depth',
      value: formatNumber(health?.command_metrics?.queue_depth, 0),
      helperText: `Inflight ${formatNumber(health?.command_metrics?.inflight, 0)}`,
      iconToken: 'queue',
    },
    {
      id: 'processing',
      label: 'Avg processing time',
      value: formatDurationMs(analyticsProfile?.average_processing_time_ms),
      helperText: `Max ${formatDurationMs(analyticsProfile?.max_processing_time_ms)} - throttled ${formatNumber(
        analyticsProfile?.throttled_frames,
        0,
      )}`,
      iconToken: 'processing-time',
    },
    {
      id: 'latency',
      label: 'Health response latency',
      value: formatDurationMs(responseTimes?.average_ms),
      helperText: `Last ${formatDurationMs(responseTimes?.last_ms)} - Max ${formatDurationMs(
        responseTimes?.max_ms,
      )}`,
      iconToken: 'latency',
    },
  ];

  const measurementState: MeasurementPanelState = (() => {
    // In archive mode, skip loading states and show static message
    if (isArchiveMode) {
      return { status: 'empty', message: 'CX-505 not connected. Browse historical sessions in the Sessions tab.' };
    }

    if (healthLoading) {
      return { status: 'loading' };
    }
    if (healthError || !health) {
      return { status: 'error', message: 'Health data unavailable.' };
    }

    const measurement = health.latest_measurement ?? null;
    if (!measurement) {
      return { status: 'empty', message: 'No measurements recorded yet.' };
    }

    return {
      status: 'ready',
      autosaveEnabled: true,
      connection: health.state === 'running' ? 'connected' : 'offline',
      logStream,
      measurement: {
        value: typeof measurement.value === 'number' ? measurement.value : undefined,
        valueText:
          measurement.value_text ??
          (typeof measurement.value === 'number'
            ? measurement.value.toString()
            : measurement.value != null
            ? String(measurement.value)
            : null),
        unit: measurement.unit ?? null,
        temperature: {
          value: measurement.temperature ?? null,
          unit: measurement.temperature_unit ?? null,
        },
        timestampIso: measurement.timestamp ?? null,
        capturedAtIso: measurement.captured_at ?? null,
        sequence: measurement.sequence ?? measurement.measurement_id ?? null,
        mode: measurement.mode ?? null,
        status: measurement.status ?? null,
        range: measurement.range ?? null,
      },
    };
  })();

  const commandHistoryEntries: CommandHistoryEntryState[] = commandHistory.map((entry) => ({
    timestampIso: entry.timestamp_iso,
    queueDepth: entry.queue_depth ?? null,
    inflight: entry.inflight ?? null,
    backlog: entry.result_backlog ?? null,
  }));

  const logEntries: DiagnosticLogRowState[] = logEvents.map((event) => ({
    id: String(event.id ?? event.created_at ?? Date.now()),
    level: normaliseLogLevel(event.level),
    category: event.category ?? 'log',
    message: event.message ?? '',
    createdAtIso: event.created_at ?? new Date().toISOString(),
  }));

  const logEmptyMessage = logEntries.length
    ? undefined
    : logStream === 'idle'
    ? 'No recent frames detected from the instrument.'
    : 'No recent log events.';

  return (
    <Stack spacing={3} sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" fontWeight={600}>
        Service Health Dashboard
      </Typography>
      <MeasurementPanel state={measurementState} metrics={metricCards} />
      <RollingChartsPanel windowMinutes={10} />
      {!isArchiveMode && (
        <>
          <CommandHistory entries={commandHistoryEntries} loading={healthLoading} />
          <LogFeed
            entries={logEntries}
            loading={logsLoading}
            errorMessage={logsError ? logsErrorObj?.message ?? 'Failed to load log stream' : null}
            emptyMessage={logEmptyMessage}
          />
        </>
      )}
    </Stack>
  );
}
