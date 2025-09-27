import { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import BugReportIcon from '@mui/icons-material/BugReport';

import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents } from '../hooks/useHealthLogEvents';
import type { HealthLogConnectionState } from '../hooks/useHealthLogEvents';
import { fetchDiagnosticBundle } from '../api/health';
import type {
  CommandMetrics,
  CommandScheduleEntry,
  DiagnosticBundleManifest,
  HealthLogEvent,
  HealthWatchdogEvent,
} from '../api/health';

import DiagnosticBundleSummaryAlert, { type BundleSummary } from './components/DiagnosticBundleSummaryAlert';

const LOG_LIST_LIMIT = 25;

const formatDateTime = (value?: string | null): string => {
  if (!value) {
    return 'Never';
  }
  try {
    return new Date(value).toLocaleString();
  } catch (_error) {
    return value;
  }
};

const formatAgeMinutes = (value?: number | null): string => {
  if (value === null || value === undefined) {
    return 'Unknown';
  }
  if (value < 1) {
    return `${Math.round(value * 60)} s ago`;
  }
  if (value >= 60) {
    const hours = value / 60;
    if (hours >= 24) {
      const days = hours / 24;
      return `${days.toFixed(1)} d ago`;
    }
    return `${hours.toFixed(1)} h ago`;
  }
  return `${value.toFixed(1)} min ago`;
};

const statusColor = (status?: string):
  | 'default'
  | 'primary'
  | 'secondary'
  | 'error'
  | 'info'
  | 'success'
  | 'warning' => {
  switch ((status || '').toLowerCase()) {
    case 'ok':
    case 'running':
      return 'success';
    case 'stale':
    case 'missing':
      return 'warning';
    case 'failed':
    case 'error':
      return 'error';
    case 'unsupported':
      return 'info';
    default:
      return 'default';
  }
};

const levelColor = (level?: string): 'default' | 'success' | 'warning' | 'error' | 'info' => {
  switch ((level || '').toLowerCase()) {
    case 'info':
      return 'info';
    case 'warning':
      return 'warning';
    case 'error':
    case 'critical':
      return 'error';
    case 'success':
      return 'success';
    default:
      return 'default';
  }
};

const watchdogColor = (kind?: string): 'default' | 'success' | 'warning' | 'error' | 'info' => {
  switch ((kind || '').toLowerCase()) {
    case 'timeout':
      return 'error';
    case 'recovery':
      return 'success';
    default:
      return 'info';
  }
};

const connectionStateColor = (state: HealthLogConnectionState): 'default' | 'success' | 'warning' | 'error' | 'info' => {
  switch (state) {
    case 'streaming':
      return 'success';
    case 'polling':
      return 'warning';
    case 'error':
      return 'error';
    case 'connecting':
    case 'loading':
      return 'info';
    default:
      return 'default';
  }
};

const connectionStateLabel = (state: HealthLogConnectionState): string => {
  switch (state) {
    case 'streaming':
      return 'Streaming';
    case 'polling':
      return 'Polling fallback';
    case 'connecting':
      return 'Connecting';
    case 'loading':
      return 'Loading';
    case 'error':
      return 'Stream error';
    default:
      return 'Idle';
  }
};

const formatCountLabel = (
  value: number | null | undefined,
  singular: string,
  plural?: string,
): string => {
  const count = value ?? 0;
  const label = count === 1 ? singular : (plural ?? singular + 's');
  return String(count) + ' ' + label;
};

const formatMaybeDate = (value?: string | null): string => (value ? formatDateTime(value) : 'Not scheduled');

export default function ServiceHealthPage() {
  const {
    data,
    isLoading,
    isFetching,
    isError,
    error,
    refetch: refetchStatus,
  } = useHealthStatus();

  const {
    data: logData,
    connectionState: logConnectionState,
    isLoading: logsLoading,
    isFetching: logsFetching,
    error: logsErrorDetail,
    refetch: refetchLogs,
  } = useHealthLogEvents(LOG_LIST_LIMIT);

  const [bundleLoading, setBundleLoading] = useState(false);
  const [bundleError, setBundleError] = useState<string | null>(null);
  const [bundleManifest, setBundleManifest] = useState<DiagnosticBundleManifest | null>(null);
  const [bundleFilename, setBundleFilename] = useState<string | null>(null);

  const logEvents = (logData ?? []) as HealthLogEvent[];

  const logConnectionLabel = useMemo(() => connectionStateLabel(logConnectionState), [logConnectionState]);
  const logConnectionChipColor = connectionStateColor(logConnectionState);
  const showLogAlert = Boolean(logsErrorDetail);
  const logAlertSeverity = logConnectionState === 'error' ? 'error' : 'warning';
  const logsRefreshing = logsFetching && !logsLoading && logConnectionState !== 'streaming';
  const watchdogHistory = (data?.watchdog_history ?? []) as HealthWatchdogEvent[];
  const commandMetrics = (data?.command_metrics ?? {}) as CommandMetrics;
  const scheduledCommands = commandMetrics.scheduled ?? [];
  const queueDepth = commandMetrics.queue_depth ?? null;
  const resultBacklog = commandMetrics.result_backlog ?? null;
  const inflightCommands = commandMetrics.inflight ?? 0;

  const logRotation = data?.log_rotation ?? null;
  const logStatus = useMemo(() => {
    if (!data) {
      return undefined;
    }
    if (!logRotation) {
      return 'disabled';
    }
    return logRotation.status || 'unknown';
  }, [data, logRotation]);

  const watchdogDetail = data?.detail && data.detail !== data.watchdog_alert ? data.detail : undefined;

  const bundleSummary = useMemo<BundleSummary | null>(() => {
    if (!bundleManifest) {
      return null;
    }
    return {
      eventsLabel: formatCountLabel(bundleManifest.counts?.events, 'log event'),
      sessionsLabel: formatCountLabel(
        bundleManifest.counts?.sessions,
        'session snapshot',
        'session snapshots',
      ),
      generatedLabel: bundleManifest.generated_at ? formatDateTime(bundleManifest.generated_at) : 'Unknown time',
      databasePath: bundleManifest.context?.database_path ?? null,
      configAvailable: bundleManifest.context?.config_available ?? null,
    };
  }, [bundleManifest]);



  const handleDownloadBundle = async () => {
    setBundleError(null);
    setBundleManifest(null);
    setBundleFilename(null);
    setBundleLoading(true);
    try {
      const { blob, filename, manifest } = await fetchDiagnosticBundle();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'elmetron_diagnostic_bundle.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setBundleManifest(manifest ?? null);
      setBundleFilename(filename);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to download diagnostic bundle';
      setBundleError(message);
    } finally {
      setBundleLoading(false);
    }
  };

  const handleRefresh = () => {
    void refetchStatus();
    void refetchLogs();
  };

  return (
    <Stack spacing={3}>
      <Card>
        <CardContent sx={{ display: 'flex', justifyContent: 'space-between', gap: 3 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" fontWeight={600} gutterBottom>
              Service Health & Diagnostics
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Monitor watchdog heartbeat, command queues, and scheduled maintenance tasks for the CX-505 capture service.
            </Typography>
            {isError ? (
              <Alert severity="error" sx={{ mt: 2 }}>
                {(error as Error).message || 'Unable to load health snapshot'}
              </Alert>
            ) : null}
            {watchdogDetail && !isError ? (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {watchdogDetail}
              </Alert>
            ) : null}
          </Box>
          <Stack spacing={1} alignItems="flex-end" justifyContent="flex-start">
            <Button
              startIcon={isFetching || logsFetching ? <CircularProgress size={16} /> : <RefreshIcon />}
              variant="outlined"
              onClick={handleRefresh}
              disabled={isLoading && logsLoading}
            >
              Refresh
            </Button>
            {data ? (
              <Chip label={`Service: ${data.state}`} color={statusColor(data.state)} size="small" sx={{ mt: 1 }} />
            ) : null}
          </Stack>
        </CardContent>
        {data ? (
          <CardContent sx={{ pt: 0 }}>
            <Divider sx={{ mb: 2 }} />
            <Box
              sx={{
                display: 'grid',
                gap: 3,
                gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(4, minmax(0, 1fr))' },
              }}
            >
              <Stat label="Frames processed" value={data.frames.toLocaleString()} />
              <Stat label="Bytes read" value={data.bytes_read.toLocaleString()} />
              <Stat label="Last frame" value={formatDateTime(data.last_frame_at)} />
              <Stat label="Capture window" value={formatDateTime(data.last_window_started)} />
            </Box>
            {data.watchdog_alert ? (
              <Alert severity="warning" sx={{ mt: 3 }}>
                {data.watchdog_alert}
              </Alert>
            ) : null}
          </CardContent>
        ) : null}
      </Card>

      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: '320px 1fr' },
        }}
      >
        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Log Rotation Task
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <Chip label={logStatus ? logStatus.toUpperCase() : 'UNKNOWN'} color={statusColor(logStatus)} size="small" />
              {logRotation?.within_threshold === false ? (
                <Chip label="Stale" color="warning" size="small" variant="outlined" />
              ) : null}
            </Stack>
            {logRotation ? (
              <Stack spacing={1}>
                <Typography variant="body2">Task name: {logRotation.name || 'Unknown'}</Typography>
                <Typography variant="body2">
                  Last run: {formatDateTime(logRotation.last_run_time)} ({formatAgeMinutes(logRotation.last_run_age_minutes)})
                </Typography>
                <Typography variant="body2">Next run: {formatDateTime(logRotation.next_run_time)}</Typography>
                <Typography variant="body2">
                  Threshold: {logRotation.threshold_minutes ? `${logRotation.threshold_minutes} min` : 'Not enforced'}
                </Typography>
                {logRotation.message ? (
                  <Typography variant="body2" color="warning.main">
                    {logRotation.message}
                  </Typography>
                ) : null}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Log rotation monitoring is disabled for this configuration.
              </Typography>
            )}
          </CardContent>
        </Card>
        <Card sx={{ minHeight: 220 }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
              <Typography variant="subtitle1" fontWeight={600}>
                Event Log Stream
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  label={logsLoading ? 'Loading…' : `${logEvents.length} events`}
                  size="small"
                  variant="outlined"
                />
                <Chip
                  label={logConnectionLabel}
                  size="small"
                  color={logConnectionChipColor}
                  variant={logConnectionState === 'streaming' ? 'filled' : 'outlined'}
                />
              </Stack>
            </Stack>
            {showLogAlert ? (
              <Alert severity={logAlertSeverity} sx={{ mb: 2 }}>
                {(logsErrorDetail as Error).message || 'Unable to load recent events'}
              </Alert>
            ) : null}
            <Box
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                p: 2,
                minHeight: 150,
                bgcolor: 'background.paper',
              }}
            >
              {logsLoading ? (
                <Stack spacing={1.5}>
                  {[0, 1, 2].map((key) => (
                    <Skeleton key={key} variant="rectangular" height={42} />
                  ))}
                </Stack>
              ) : logEvents.length ? (
                <List dense disablePadding>
                  {logEvents.map((event: HealthLogEvent, index: number) => (
                    <ListItem key={event.id} disableGutters sx={{ pb: index === logEvents.length - 1 ? 0 : 1.5 }}>
                      <Stack spacing={0.5} sx={{ width: '100%' }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Chip label={event.level.toUpperCase()} size="small" color={levelColor(event.level)} />
                            <Typography variant="body2" fontWeight={600}>
                              {event.category}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {formatDateTime(event.created_at)}
                            </Typography>
                          </Stack>
                          {logsRefreshing && index === 0 ? <CircularProgress size={14} /> : null}
                        </Stack>
                        <ListItemText
                          primaryTypographyProps={{ variant: 'body2' }}
                          secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
                          primary={event.message}
                          secondary={event.payload ? JSON.stringify(event.payload) : undefined}
                          sx={{ margin: 0 }}
                        />
                      </Stack>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No events recorded yet. Start a capture session or run a calibration command to see activity here.
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
        }}
      >
        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Watchdog Timeline
            </Typography>
            <Box
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                p: 2,
                minHeight: 150,
                bgcolor: 'background.paper',
              }}
            >
              {watchdogHistory.length ? (
                <List dense disablePadding>
                  {watchdogHistory.map((event: HealthWatchdogEvent, index: number) => (
                    <ListItem
                      key={`${event.occurred_at}-${event.kind}`}
                      disableGutters
                      sx={{ pb: index === watchdogHistory.length - 1 ? 0 : 1.5 }}
                    >
                      <Stack spacing={0.5} sx={{ width: '100%' }}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Chip label={event.kind.toUpperCase()} size="small" color={watchdogColor(event.kind)} />
                          <Typography variant="body2" fontWeight={600}>
                            {event.message}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatDateTime(event.occurred_at)}
                          </Typography>
                        </Stack>
                        {event.payload ? (
                          <Typography variant="caption" color="text.secondary">
                            {JSON.stringify(event.payload)}
                          </Typography>
                        ) : null}
                      </Stack>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No watchdog activity recorded yet.
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Command Queue Metrics
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip label={`Queue: ${queueDepth ?? 'n/a'}`} size="small" />
              <Chip label={`Results: ${resultBacklog ?? 'n/a'}`} size="small" />
              <Chip label={`In-flight: ${inflightCommands}`} size="small" />
              <Chip
                label={commandMetrics.worker_running ? 'Worker running' : 'Worker idle'}
                size="small"
                color={commandMetrics.worker_running ? 'success' : 'default'}
              />
              <Chip
                label={commandMetrics.async_enabled ? 'Async enabled' : 'Sync mode'}
                size="small"
                variant="outlined"
              />
            </Stack>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom>
              Scheduled Commands
            </Typography>
            {scheduledCommands.length ? (
              <List dense disablePadding>
                {scheduledCommands.map((item: CommandScheduleEntry, index: number) => (
                  <ListItem
                    key={`${item.name}-${index}`}
                    disableGutters
                    sx={{ pb: index === scheduledCommands.length - 1 ? 0 : 1.5 }}
                  >
                    <Stack spacing={0.25} sx={{ width: '100%' }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" fontWeight={600}>
                          {item.name}
                        </Typography>
                        <Chip
                          label={item.active ? 'Active' : 'Paused'}
                          size="small"
                          color={item.active ? 'success' : 'default'}
                        />
                        {item.in_flight ? <Chip label="Running" size="small" color="warning" /> : null}
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        Next run: {formatMaybeDate(item.next_due_iso)}
                      </Typography>
                      {item.last_error ? (
                        <Typography variant="caption" color="error">
                          Last error: {item.last_error}
                        </Typography>
                      ) : null}
                    </Stack>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No scheduled commands configured.
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
        }}
      >
        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Configuration Snapshot
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Device index, poll sequence, startup commands, export defaults.
            </Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Command Queue
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View active/scheduled protocol commands with ability to pause or reprioritise.
            </Typography>
            <Button
              startIcon={bundleLoading ? <CircularProgress size={16} /> : <BugReportIcon />}
              sx={{ mt: 2 }}
              onClick={handleDownloadBundle}
              disabled={bundleLoading}
            >
              {bundleLoading ? 'Preparing bundle...' : 'Download Diagnostic Bundle'}
            </Button>
            {bundleError ? (
              <Alert severity="error" sx={{ mt: 2 }}>
                {bundleError}
              </Alert>
            ) : null}
            {bundleManifest && bundleSummary ? (
              <DiagnosticBundleSummaryAlert
                summary={bundleSummary}
                filename={bundleFilename}
                onClose={() => {
                  setBundleManifest(null);
                  setBundleFilename(null);
                }}
              />
            ) : null}
          </CardContent>
        </Card>
      </Box>
    </Stack>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="subtitle2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h6" fontWeight={600}>
        {value}
      </Typography>
    </Box>
  );
}

















