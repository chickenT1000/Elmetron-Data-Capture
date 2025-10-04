import { Stack, Typography } from '@mui/material';
import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents, type HealthLogConnectionState } from '../hooks/useHealthLogEvents';
import { useLiveStatus } from '../hooks/useLiveStatus';
import { MeasurementPanel } from '../components/MeasurementPanel';
import { RollingChartsPanel } from '../components/RollingChartsPanel';
import type {
  MeasurementPanelState,
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



export default function DashboardPage() {
  const { data: liveStatus } = useLiveStatus();
  const isArchiveMode = liveStatus?.mode === 'archive';

  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
  } = useHealthStatus(2000);

  const {
    connectionState,
  } = useHealthLogEvents({ limit: 25, fallbackMs: 5000 });

  const logStream = normaliseLogStream(connectionState);

  const measurementState: MeasurementPanelState = (() => {
    // In archive mode, skip loading states and show static message
    if (isArchiveMode) {
      return { status: 'empty', message: 'Device not connected. Browse historical sessions in the Sessions tab.' };
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



  return (
    <Stack spacing={3} sx={{ py: 3 }}>
      <MeasurementPanel state={measurementState} />
      <RollingChartsPanel windowMinutes={10} />
    </Stack>
  );
}
