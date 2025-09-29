import { Box, Stack, Typography, Divider } from '@mui/material';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import StorageIcon from '@mui/icons-material/Storage';
import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents } from '../hooks/useHealthLogEvents';
import { MeasurementPanel } from '../components/MeasurementPanel';
import type { MeasurementPanelState, MetricIndicatorState } from '../components/contracts';
import { CommandHistory } from '../components/CommandHistory';
import { LogFeed } from '../components/LogFeed';

const formatNumber = (value?: number | null, digits = 2): string => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return '—';
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
};

const formatDurationMs = (value?: number | null): string => {
  if (!value && value !== 0) return '—';
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`;
  }
  return `${value.toFixed(1)} ms`;
};

export default function DashboardPage() {
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
      iconToken: 'frames',
    },
    {
      id: 'processing',
      label: 'Avg processing time',
      value: formatDurationMs(analyticsProfile?.average_processing_time_ms),
      helperText: `Max ${formatDurationMs(analyticsProfile?.max_processing_time_ms)} • throttled ${formatNumber(
        analyticsProfile?.throttled_frames,
        0,
      )}`,
      iconToken: 'processing-time',
    },
    {
      id: 'latency',
      label: 'Health response latency',
      value: formatDurationMs(responseTimes?.average_ms),
      helperText: `Last ${formatDurationMs(responseTimes?.last_ms)} • Max ${formatDurationMs(responseTimes?.max_ms)}`,
      iconToken: 'latency',
    },
  ];

  const measurementState: MeasurementPanelState = (() => {
    if (healthLoading) {
      return { status: 'loading' };
    }
    if (healthError) {
      return { status: 'error', message: 'Health data unavailable.' };
    }

    const measurement = health?.latest_measurement ?? null;
    if (!measurement) {
      return { status: 'empty', message: 'No measurements recorded yet.' };
    }

    return {
      status: 'ready',
      autosaveEnabled: true,
      connection: health?.state === 'running' ? 'connected' : 'offline',
      logStream: connectionState,
      measurement: {
        value: typeof measurement.value === 'number' ? measurement.value : undefined,
        valueText: measurement.value_text ?? measurement.value?.toString() ?? null,
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

  const commandHistoryEntries = commandHistory.map((entry) => ({
    timestampIso: entry.timestamp_iso,
    queueDepth: entry.queue_depth,
    inflight: entry.inflight,
    backlog: entry.result_backlog,
  }));

  const logEntries = logEvents.map((event) => ({
    id: event.id,
    level: event.level as MetricIndicatorState['tone'],
    category: event.category,
    message: event.message,
    createdAtIso: event.created_at,
  }));
    : 'No recent frames detected from the instrument.';

  return (
      <MeasurementPanel state={measurementState} metrics={metricCards} />
      </Card>
      <CommandHistory entries={commandHistoryEntries} loading={healthLoading} />
      </Card>
      <LogFeed
        entries={logEntries}
        loading={logsLoading}
        errorMessage={logsError ? logsErrorObj?.message ?? 'Failed to load log stream' : null}
      />
      </Card>
    </Stack>
  );
}
