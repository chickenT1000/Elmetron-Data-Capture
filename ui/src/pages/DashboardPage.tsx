import { Box, Card, CardContent, CircularProgress, Stack, Typography, Alert, Divider, Chip } from '@mui/material';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import SensorsIcon from '@mui/icons-material/Sensors';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import StorageIcon from '@mui/icons-material/Storage';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import type { HealthLogEvent } from '../api/health';
import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents } from '../hooks/useHealthLogEvents';

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

const renderMetricCard = (
  label: string,
  value: string,
  helper?: string,
  Icon?: typeof SensorsIcon,
) => (
  <Card key={label}>
    <CardContent>
      <Stack direction="row" spacing={1} alignItems="center" mb={1}>
        {Icon ? <Icon color="primary" fontSize="small" /> : null}
        <Typography variant="subtitle2" color="text.secondary">
          {label}
        </Typography>
      </Stack>
      <Typography variant="h4" fontWeight={600}>
        {value}
      </Typography>
      {helper ? (
        <Typography variant="caption" color="text.secondary">
          {helper}
        </Typography>
      ) : null}
    </CardContent>
  </Card>
);

const renderLogRow = (event: HealthLogEvent) => (
  <Stack key={event.id} direction="row" spacing={1} alignItems="flex-start">
    <Chip
      size="small"
      label={event.level}
      color={event.level === 'warning' || event.level === 'error' ? 'warning' : 'default'}
      sx={{ textTransform: 'capitalize' }}
    />
    <Box>
      <Typography variant="body2" fontWeight={600}>
        {event.category}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {event.message}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {event.created_at}
      </Typography>
    </Box>
  </Stack>
);

export default function DashboardPage() {
  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
    commandHistory,
    analyticsProfile,
    responseTimes,
  } = useHealthStatus();

  const logLimit = 25;
  const {
    data: logEvents,
    connectionState,
    isLoading: logsLoading,
    isError: logsError,
    error: logsErrorObj,
  } = useHealthLogEvents({ limit: logLimit, fallbackMs: 5000 });

  const metricCards = [
    {
      label: 'Frames Processed',
      value: formatNumber(health?.frames, 0),
      helper: `Bytes read ${formatNumber(health?.bytes_read, 0)}`,
      Icon: SensorsIcon,
    },
    {
      label: 'Command queue depth',
      value: formatNumber(health?.command_metrics?.queue_depth, 0),
      helper: `Inflight ${formatNumber(health?.command_metrics?.inflight, 0)}`,
      Icon: StorageIcon,
    },
    {
      label: 'Avg processing time',
      value: formatDurationMs(analyticsProfile?.average_processing_time_ms),
      helper: `Max ${formatDurationMs(analyticsProfile?.max_processing_time_ms)} • throttled ${formatNumber(
        analyticsProfile?.throttled_frames,
        0,
      )}`,
      Icon: WarningAmberIcon,
    },
    {
      label: 'Health response latency',
      value: formatDurationMs(responseTimes?.average_ms),
      helper: `Last ${formatDurationMs(responseTimes?.last_ms)} • Max ${formatDurationMs(responseTimes?.max_ms)}`,
      Icon: AccessTimeIcon,
    },
  ];

  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
            <Box>
              <Typography variant="h5" fontWeight={600} gutterBottom>
                Live Monitoring & Telemetry
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Observability across the CX-505 capture stack, including throughput, command activity, and alert stream.
              </Typography>
            </Box>
            <Stack direction="row" spacing={2} alignItems="center">
              {healthLoading ? <CircularProgress size={20} /> : null}
              {healthError ? <Chip color="error" label="Health data unavailable" /> : null}
              <Chip
                color={connectionState === 'streaming' ? 'success' : connectionState === 'polling' ? 'warning' : 'default'}
                label={`Logs: ${connectionState}`}
                sx={{ textTransform: 'capitalize' }}
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        }}
      >
        {metricCards.map((metric) =>
          renderMetricCard(metric.label, metric.value, metric.helper, metric.Icon),
        )}
      </Box>

      <Card sx={{ minHeight: 360 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} mb={2}>
            <ShowChartIcon color="primary" />
            <Typography variant="h6">Command Throughput (History)</Typography>
          </Stack>
          {commandHistory.length === 0 ? (
            <Box
              sx={{
                borderRadius: 2,
                border: '1px dashed',
                borderColor: 'divider',
                height: 240,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'text.secondary',
              }}
            >
              {healthLoading ? 'Loading telemetry…' : 'No command history available yet.'}
            </Box>
          ) : (
            <Box
              sx={{
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                height: 240,
                p: 2,
                overflow: 'auto',
                display: 'grid',
                gap: 1,
              }}
            >
              {commandHistory.map((entry) => (
                <Stack key={entry.timestamp} direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2" sx={{ minWidth: 180 }} color="text.secondary">
                    {entry.timestamp_iso}
                  </Typography>
                  <Typography variant="body2">Queue {formatNumber(entry.queue_depth, 0)}</Typography>
                  <Typography variant="body2">Inflight {formatNumber(entry.inflight, 0)}</Typography>
                  <Typography variant="body2">Backlog {formatNumber(entry.result_backlog, 0)}</Typography>
                </Stack>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      <Card sx={{ minHeight: 320 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} mb={2}>
            <WarningAmberIcon color="warning" />
            <Typography variant="h6">Live Alerts & Diagnostics</Typography>
          </Stack>
          {logsError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {logsErrorObj?.message ?? 'Failed to load log stream'}
            </Alert>
          ) : null}
          <Stack spacing={2} divider={<Divider flexItem light />}>
            {logsLoading && logEvents.length === 0 ? (
              <Stack alignItems="center" py={4} spacing={1}>
                <CircularProgress size={24} />
                <Typography variant="body2" color="text.secondary">
                  Connecting to log stream…
                </Typography>
              </Stack>
            ) : logEvents.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No recent log events.
              </Typography>
            ) : (
              logEvents.map((event) => renderLogRow(event))
            )}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
