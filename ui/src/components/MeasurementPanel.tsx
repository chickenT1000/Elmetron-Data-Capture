import React from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SensorsIcon from '@mui/icons-material/Sensors';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import type { MeasurementPanelState, MetricIndicatorState } from './contracts';

const formatNumber = (value?: number | null, digits = 2): string => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return '—';
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
};

const formatTimestamp = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

const formatTemperature = (value?: number | null, unit?: string | null): string => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return '—';
  }
  const display = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return unit ? `${display} ${unit}` : display;
};

const renderMetricCard = (metric: MetricIndicatorState) => {
  const icon = (() => {
    switch (metric.iconToken) {
      case 'frames':
        return SensorsIcon;
      case 'processing-time':
        return WarningAmberIcon;
      case 'latency':
        return AccessTimeIcon;
      default:
        return undefined;
    }
  })();

  const IconComponent = icon;

  return (
    <Card key={metric.id}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" mb={1}>
          {IconComponent ? <IconComponent color="primary" fontSize="small" /> : null}
          <Typography variant="subtitle2" color="text.secondary">
            {metric.label}
          </Typography>
        </Stack>
        <Typography variant="h4" fontWeight={600}>
          {metric.value}
        </Typography>
        {metric.helperText ? (
          <Typography variant="caption" color="text.secondary">
            {metric.helperText}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
};

export interface MeasurementPanelProps {
  state: MeasurementPanelState;
  metrics?: MetricIndicatorState[];
}

export const MeasurementPanel: React.FC<MeasurementPanelProps> = ({ state, metrics }) => {
  if (state.status === 'loading') {
    return (
      <Box
        sx={{
          borderRadius: 2,
          border: '1px dashed',
          borderColor: 'divider',
          px: 3,
          py: 6,
          textAlign: 'center',
          color: 'text.secondary',
        }}
      >
        <Stack alignItems="center" spacing={2}>
          <CircularProgress size={28} />
          <Typography variant="body2">Waiting for first measurement…</Typography>
        </Stack>
      </Box>
    );
  }

  if (state.status === 'error') {
    return <Alert severity="error">{state.message}</Alert>;
  }

  if (state.status === 'empty') {
    return (
      <Box
        sx={{
          borderRadius: 2,
          border: '1px dashed',
          borderColor: 'divider',
          px: 3,
          py: 6,
          textAlign: 'center',
          color: 'text.secondary',
        }}
      >
        <Typography variant="body2">{state.message ?? 'No measurements recorded yet.'}</Typography>
      </Box>
    );
  }

  const measurement = state.measurement;
  const measurementDigits =
    measurement?.unit && measurement.unit.toLowerCase().includes('ph') ? 2 : 3;
  
  // Check if device is in TIME mode
  // TIME mode is detected when valueText looks like time format (HH:MM) AND there's no numeric value
  const isTimeMode = 
    measurement?.mode?.toUpperCase() === 'TIME' || 
    (measurement?.valueText && typeof measurement?.value !== 'number' && /^\d{1,2}:\d{2}(:\d{2})?$/.test(measurement.valueText.trim()));
  
  const measurementValue =
    typeof measurement?.value === 'number'
      ? formatNumber(measurement.value, measurementDigits)
      : isTimeMode && measurement?.valueText
      ? measurement.valueText
      : measurement?.valueText ?? '—';
  const measurementUnit = isTimeMode ? '' : (measurement?.unit ?? '').replace(/\s*rel\.?$/i, '');
  const temperatureDisplay = formatTemperature(
    measurement?.temperature?.value,
    measurement?.temperature?.unit,
  );
  // Always use PC capture time, not device timestamp (device clock may be wrong, especially in TIME mode)
  const lastUpdatedIso = measurement?.capturedAtIso ?? measurement?.timestampIso ?? null;
  const connectionChipColor = state.connection === 'connected' ? 'success' : state.connection === 'error' ? 'error' : 'default';
  const connectionChipLabel = state.connection === 'connected' ? 'CX-505 connected' : state.connection === 'error' ? 'Health data unavailable' : 'CX-505 offline';
  const connectionChipTooltip = state.connection === 'connected'
    ? 'Instrument link healthy and streaming frames.'
    : state.connection === 'error'
    ? 'Unable to retrieve instrument health data.'
    : 'No recent frames detected from the instrument.';
  const logChipColor = state.logStream === 'streaming' ? 'success' : state.logStream === 'polling' ? 'success' : 'default';

  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Stack spacing={3}>
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              justifyContent="space-between"
              alignItems={{ xs: 'flex-start', md: 'center' }}
              spacing={2}
            >
              <Box>
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  Live CX-505 Measurements
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Latest readings update automatically while the capture service is running.
                </Typography>
              </Box>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Tooltip title={connectionChipTooltip} placement="top">
                  <Chip color={connectionChipColor} label={connectionChipLabel} />
                </Tooltip>
                <Tooltip
                  title="Session logging starts automatically on launch and persists to the local database."
                  placement="top"
                >
                  <Chip color={state.autosaveEnabled ? 'success' : 'default'} label={state.autosaveEnabled ? 'Autosave on' : 'Autosave off'} />
                </Tooltip>
                <Tooltip title={`Log stream state: ${state.logStream}`} placement="top">
                  <Chip
                    color={logChipColor}
                    label={`Logs: ${state.logStream}`}
                    sx={{ textTransform: 'capitalize' }}
                  />
                </Tooltip>
              </Stack>
            </Stack>

            {isTimeMode && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  <strong>Device in TIME mode:</strong> The meter is currently displaying time and is not sending measurement data. 
                  Switch the device to measurement mode to resume data collection.
                </Typography>
              </Alert>
            )}

            {measurementValue === '—' && !measurement?.temperature ? (
              <Box
                sx={{
                  borderRadius: 2,
                  border: '1px dashed',
                  borderColor: 'divider',
                  px: 3,
                  py: 6,
                  textAlign: 'center',
                  color: 'text.secondary',
                }}
              >
                <Typography variant="body2">No valid measurement data.</Typography>
              </Box>
            ) : (
              <Stack spacing={3}
              >
                <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'baseline', gap: 6 }}>
                  <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'baseline', gap: 2, minWidth: 450 }}>
                    <Typography variant="h5" color="text.secondary" fontWeight={500} sx={{ display: 'inline-block', width: 140 }}>
                      {measurementUnit?.toLowerCase().includes('ph') ? 'pH' :
                       measurementUnit?.toLowerCase().includes('mv') ? 'Redox' :
                       measurementUnit?.toLowerCase().includes('µs') || measurementUnit?.toLowerCase().includes('us') ? 'Conductivity' :
                       measurementUnit ? measurementUnit : 'pH'}
                    </Typography>
                    <Typography variant="h2" fontWeight={700}>
                      {measurementValue}
                    </Typography>
                    {measurementUnit && !measurementUnit.toLowerCase().includes('ph') ? (
                      <Typography variant="h5" color="text.secondary">
                        {measurementUnit}
                      </Typography>
                    ) : null}
                  </Box>
                  <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
                    <Typography variant="h5" color="text.secondary" fontWeight={500}>
                      Temperature
                    </Typography>
                    <Typography variant="h2" fontWeight={700}>
                      {measurement?.temperature?.value !== null && measurement?.temperature?.value !== undefined
                        ? formatNumber(measurement.temperature.value, 1)
                        : '—'}
                    </Typography>
                    {measurement?.temperature?.unit ? (
                      <Typography variant="h5" color="text.secondary">
                        {measurement.temperature.unit.replace(/deg\s*/gi, '°')}
                      </Typography>
                    ) : null}
                  </Box>
                </Box>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Last update: {formatTimestamp(lastUpdatedIso)}
                  </Typography>
                </Box>
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>

      {metrics && metrics.length > 0 ? (
        <Box
          sx={{
            display: 'grid',
            gap: 3,
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          }}
        >
          {metrics.map(renderMetricCard)}
        </Box>
      ) : null}
    </Stack>
  );
};

export default MeasurementPanel;
