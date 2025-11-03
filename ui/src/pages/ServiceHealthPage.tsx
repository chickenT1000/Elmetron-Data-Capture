import { useEffect, useMemo, useState } from 'react';
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
import BugReportIcon from '@mui/icons-material/BugReport';

import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents } from '../hooks/useHealthLogEvents';
import type { HealthLogConnectionState } from '../hooks/useHealthLogEvents';
import { useLiveStatus } from '../hooks/useLiveStatus';
import { fetchDiagnosticBundle } from '../api/health';
import type {
  CommandMetrics,
  CommandScheduleEntry,
  DiagnosticBundleManifest,
  HealthLogEvent,
  HealthWatchdogEvent,
} from '../api/health';

import DiagnosticBundleSummaryAlert, { type BundleSummary } from './components/DiagnosticBundleSummaryAlert';

const LOG_LIST_LIMIT = 999; // Show up to 999 events

const formatDateTime = (value?: string | null): string => {
  if (!value) {
    return 'Never';
  }
  
  // Normalize timestamp: replace space with T, ensure Z suffix for UTC timestamps
  let normalized = value.replace(' ', 'T');
  if (!normalized.includes('+') && !normalized.endsWith('Z')) {
    normalized += 'Z';  // Assume UTC if no timezone indicator
  }
  
  const time = new Date(normalized);
  if (Number.isNaN(time.getTime())) {
    return value; // Return original if parsing fails
  }
  
  return time.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false, // 24-hour format
  });
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
    case 'polling':  // Polling is normal, not an error!
      return 'success';
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
      return 'Polling';  // Remove "fallback" - polling is normal!
    case 'connecting':
      return 'Connecting';
    case 'loading':
      return 'Loading';
    case 'error':
      return 'Connection error';
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
  const { data: liveStatus } = useLiveStatus();
  const isArchiveMode = liveStatus?.mode === 'archive';

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
  } = useHealthLogEvents({ 
    limit: LOG_LIST_LIMIT,
    // Filter out DEBUG logs - show only INFO and above for typical users
    level: 'INFO'
  });

  const [bundleLoading, setBundleLoading] = useState(false);
  const [bundleError, setBundleError] = useState<string | null>(null);
  const [bundleManifest, setBundleManifest] = useState<DiagnosticBundleManifest | null>(null);
  const [bundleFilename, setBundleFilename] = useState<string | null>(null);
  const [autoRefreshCountdown, setAutoRefreshCountdown] = useState(30);

  const logEvents = (logData ?? []) as HealthLogEvent[];

  const logConnectionLabel = useMemo(() => connectionStateLabel(logConnectionState), [logConnectionState]);
  const logConnectionChipColor = connectionStateColor(logConnectionState);
  const showLogAlert = logConnectionState === 'error' && Boolean(logsErrorDetail);
  const logAlertSeverity = 'error';
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
    setAutoRefreshCountdown(30); // Reset countdown after manual refresh
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setAutoRefreshCountdown((prev) => {
        if (prev <= 1) {
          void refetchStatus();
          void refetchLogs();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [refetchStatus, refetchLogs]);

  // In archive mode, don't show health monitoring at all
  if (isArchiveMode) {
    return (
      <Stack spacing={3}>
        <Card>
          <CardContent>
            <Typography variant="h5" fontWeight={600} gutterBottom>
              Service Health & Diagnostics
            </Typography>
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body1" gutterBottom>
                <strong>Archive Mode</strong> - Live capture service not available
              </Typography>
              <Typography variant="body2">
                The CX-505 device is not connected. Health monitoring requires an active capture service.
                You can browse historical measurement sessions in the <strong>Sessions</strong> tab.
              </Typography>
            </Alert>
          </CardContent>
        </Card>
      </Stack>
    );
  }

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
            {isArchiveMode && isError ? (
              <Alert severity="info" sx={{ mt: 2 }}>
                <strong>Archive Mode</strong> - The CX-505 device is not connected. Live health monitoring is unavailable, but you can browse historical sessions in the Sessions tab.
              </Alert>
            ) : isError ? (
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
            <Typography variant="caption" color="text.secondary">
              Auto-refresh in {autoRefreshCountdown}s
            </Typography>
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

      {/* Event Log Stream - full width */}
      <Card>
        <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
              <Typography variant="subtitle1" fontWeight={600}>
                Event Log Stream
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  label={logsLoading ? 'Loading…' : `${logEvents.filter(e => e.level.toUpperCase() !== 'DEBUG').length} events`}
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
                {(logsErrorDetail as Error).message || 'Unable to connect to log stream'}
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
                  {logEvents.map((event: HealthLogEvent, index: number) => {
                    // Filter out DEBUG logs on frontend as well (backup)
                    if (event.level.toUpperCase() === 'DEBUG') {
                      return null;
                    }
                    
                    // Compact single-row format: [LEVEL] category - message {payload}
                    const payloadText = event.payload ? ` ${JSON.stringify(event.payload)}` : '';
                    const fullText = `${event.message}${payloadText}`;
                    
                    return (
                      <ListItem key={event.id} disableGutters sx={{ pb: index === logEvents.length - 1 ? 0 : 1 }}>
                        <Stack direction="row" spacing={1} alignItems="center" sx={{ width: '100%' }}>
                          <Chip label={event.level.toUpperCase()} size="small" color={levelColor(event.level)} />
                          <Typography variant="body2" fontWeight={600}>
                            {event.category}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
                            - {fullText}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
                            {formatDateTime(event.created_at)}
                          </Typography>
                        </Stack>
                      </ListItem>
                    );
                  })}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No events recorded yet. Start a capture session or run a calibration command to see activity here.
                </Typography>
              )}
            </Box>
        </CardContent>
      </Card>

      {/* Only show Watchdog Timeline if there are actual events */}
      {watchdogHistory.length > 0 && (
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
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Diagnostic Bundle Download */}
      <Card>
        <CardContent>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Diagnostic Bundle
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Download a diagnostic bundle containing system logs, configuration, and health data for troubleshooting.
            Logs are automatically cleaned at application startup (deletes logs older than 30 days). Download diagnostic bundles regularly to preserve historical data.
          </Typography>
          <Button
            startIcon={bundleLoading ? <CircularProgress size={16} /> : <BugReportIcon />}
            onClick={handleDownloadBundle}
            disabled={bundleLoading}
            variant="outlined"
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

















