import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  InputLabel,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import ImageIcon from '@mui/icons-material/Image';
import TimelineIcon from '@mui/icons-material/Timeline';
import { useQueries, type UseQueryResult } from '@tanstack/react-query';
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis, Legend } from 'recharts';
import { toPng } from 'html-to-image';

import {
  downloadSessionEvaluationJson,
  type SessionEvaluationMarker,
  type SessionEvaluationResponse,
} from '../api/sessions';
import { useRecentSessions } from '../hooks/useRecentSessions';
import { sessionEvaluationQueryOptions } from '../hooks/useSessionEvaluation';

const COLOR_PALETTE = ['#1976d2', '#d81b60', '#2e7d32', '#f57c00', '#6d4c41', '#8e24aa'];

const formatDateTime = (value?: string | null): string => {
  if (!value) {
    return 'Unknown';
  }
  try {
    return new Date(value).toLocaleString();
  } catch (_error) {
    return value;
  }
};

const formatNumber = (value?: number | null, digits = 2): string => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return '—';
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
};

const formatDuration = (value?: number | null): string => {
  if (value === undefined || value === null) {
    return '—';
  }
  const abs = Math.abs(value);
  if (abs >= 3600) {
    const hours = value / 3600;
    return `${hours.toFixed(2)} h`;
  }
  if (abs >= 60) {
    const minutes = value / 60;
    return `${minutes.toFixed(2)} min`;
  }
  return `${value.toFixed(2)} s`;
};

const formatOffset = (value?: number | null): string => {
  if (value === undefined || value === null) {
    return '—';
  }
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  const abs = Math.abs(value);
  if (abs >= 60) {
    const minutes = abs / 60;
    return `${sign}${minutes.toFixed(2)} min`;
  }
  return `${sign}${abs.toFixed(2)} s`;
};

const ANCHOR_OPTIONS = [
  { value: 'start', label: 'Align by session start' },
  { value: 'calibration', label: 'Align by first calibration marker' },
];

const buildFilename = (extension: string) => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return `session_evaluation_${timestamp}.${extension}`;
};

const mergeSeriesForChart = (evaluations: SessionEvaluationResponse[]) => {
  const merged = new Map<string, Record<string, number | string>>();
  evaluations.forEach((evaluation) => {
    const keyName = `session_${evaluation.session.id}`;
    evaluation.series.forEach((point, index) => {
      if (point.offset_seconds === null || point.offset_seconds === undefined) {
        const key = `idx_${evaluation.session.id}_${index}`;
        const bucket = merged.get(key) ?? { key: index, label: index };
        if (point.value !== null && point.value !== undefined) {
          bucket[keyName] = point.value;
        }
        merged.set(key, bucket);
        return;
      }
      const key = point.offset_seconds.toFixed(3);
      const bucket = merged.get(key) ?? {
        offset_seconds: point.offset_seconds,
      };
      if (point.value !== null && point.value !== undefined) {
        bucket[keyName] = point.value;
      }
      merged.set(key, bucket);
    });
  });
  const result = Array.from(merged.values()).map((entry) => ({
    offset_seconds: typeof entry.offset_seconds === 'number' ? entry.offset_seconds : null,
    ...entry,
  }));
  result.sort((a, b) => {
    const left = typeof a.offset_seconds === 'number' ? a.offset_seconds : Number(a.key ?? 0);
    const right = typeof b.offset_seconds === 'number' ? b.offset_seconds : Number(b.key ?? 0);
    return left - right;
  });
  return result;
};

const buildExportEnvelope = (evaluations: SessionEvaluationResponse[], anchor: string) => ({
  generated_at: new Date().toISOString(),
  anchor,
  sessions: evaluations.map((evaluation) => ({
    session: evaluation.session,
    anchor: evaluation.anchor,
    anchor_timestamp: evaluation.anchor_timestamp,
    statistics: evaluation.statistics,
    markers: evaluation.markers,
    duration_seconds: evaluation.duration_seconds,
    samples: evaluation.samples,
    series: evaluation.series,
  })),
});

export default function SessionEvaluationPage() {
  const [anchor, setAnchor] = useState<'start' | 'calibration'>('start');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingPng, setExportingPng] = useState(false);
  const chartRef = useRef<HTMLDivElement | null>(null);

  const {
    data: sessions,
    isLoading: sessionsLoading,
    isError: sessionsError,
    error: sessionsErrorDetail,
  } = useRecentSessions(10);

  useEffect(() => {
    if (!sessionsLoading && !sessionsError && sessions && sessions.length && selectedIds.length === 0) {
      setSelectedIds([sessions[0].id]);
    }
  }, [sessions, sessionsLoading, sessionsError, selectedIds.length]);

  const evaluationQueries = useQueries({
    queries: selectedIds.map((sessionId) => ({
      ...sessionEvaluationQueryOptions(sessionId, anchor),
      enabled: true,
    })),
  }) as UseQueryResult<SessionEvaluationResponse>[];

  const evaluations = useMemo(
    () => evaluationQueries.map((query) => query.data).filter(Boolean) as SessionEvaluationResponse[],
    [evaluationQueries],
  );

  const chartData = useMemo(() => mergeSeriesForChart(evaluations), [evaluations]);

  const colorBySession = useMemo(() => {
    const map = new Map<number, string>();
    evaluations.forEach((evaluation, index) => {
      const color = COLOR_PALETTE[index % COLOR_PALETTE.length];
      map.set(evaluation.session.id, color);
    });
    return map;
  }, [evaluations]);

  const combinedMarkers = useMemo(() => {
    const markers: (SessionEvaluationMarker & { session_id: number })[] = [];
    evaluations.forEach((evaluation) => {
      evaluation.markers.forEach((marker) => {
        markers.push({ ...marker, session_id: evaluation.session.id });
      });
    });
    return markers;
  }, [evaluations]);

  const evaluationLoading = evaluationQueries.some((query) => query.isLoading || query.isFetching);
  const evaluationError = evaluationQueries
    .map((query) => query.error)
    .find((error) => error instanceof Error) as Error | undefined;

  const toggleSession = (sessionId: number) => {
    setSelectedIds((previous) =>
      previous.includes(sessionId)
        ? previous.filter((id) => id !== sessionId)
        : [...previous, sessionId],
    );
  };

  const handleExportJson = async () => {
    if (!evaluations.length) {
      return;
    }
    const payload = buildExportEnvelope(evaluations, anchor);
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = buildFilename('json');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  };

  const handleExportPng = async () => {
    if (!chartRef.current || !evaluations.length) {
      return;
    }
    try {
      setExportError(null);
      setExportingPng(true);
      const dataUrl = await toPng(chartRef.current, {
        cacheBust: true,
        backgroundColor: '#ffffff',
      });
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = buildFilename('png');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to export PNG';
      setExportError(message);
    } finally {
      setExportingPng(false);
    }
  };

  const handleDownloadSessionJson = async () => {
    if (!selectedIds.length) {
      return;
    }
    try {
      const [sessionId] = selectedIds;
      const filename = buildFilename('json');
      const blob = await downloadSessionEvaluationJson(sessionId, {
        anchor,
        filename,
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to download evaluation';
      setExportError(message);
    }
  };

  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Stack spacing={2} direction={{ xs: 'column', md: 'row' }} justifyContent="space-between">
            <Box>
              <Typography variant="h5" fontWeight={600} gutterBottom>
                Session Evaluation & Overlays
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Align recent sessions, compare derived metrics, and export overlay evidence for calibration reviews.
              </Typography>
            </Box>
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel id="anchor-select">Alignment</InputLabel>
                <Select
                  labelId="anchor-select"
                  value={anchor}
                  label="Alignment"
                  onChange={(event) => setAnchor(event.target.value as 'start' | 'calibration')}
                >
                  {ANCHOR_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="outlined"
                startIcon={<TimelineIcon />}
                disabled={!selectedIds.length}
                onClick={handleDownloadSessionJson}
              >
                Export session JSON
              </Button>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                disabled={!evaluations.length}
                onClick={handleExportJson}
              >
                Export combined JSON
              </Button>
              <Button
                variant="contained"
                startIcon={<ImageIcon />}
                disabled={!evaluations.length || exportingPng}
                onClick={handleExportPng}
              >
                {exportingPng ? 'Rendering…' : 'Export PNG'}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {exportError ? (
        <Alert severity="error" onClose={() => setExportError(null)}>
          {exportError}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '320px 1fr' },
          gap: 3,
        }}
      >
        <Card sx={{ minHeight: 360 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Session catalogue
            </Typography>
            {sessionsLoading ? (
              <Stack alignItems="center" py={4} spacing={1}>
                <CircularProgress size={24} />
                <Typography variant="body2" color="text.secondary">
                  Loading recent sessions…
                </Typography>
              </Stack>
            ) : sessionsError ? (
              <Alert severity="error">
                {(sessionsErrorDetail as Error | undefined)?.message ?? 'Unable to load sessions'}
              </Alert>
            ) : !sessions?.length ? (
              <Typography variant="body2" color="text.secondary">
                No recent sessions were found in the archive.
              </Typography>
            ) : (
              <List disablePadding>
                {sessions.map((session) => {
                  const selected = selectedIds.includes(session.id);
                  return (
                    <ListItemButton
                      key={session.id}
                      onClick={() => toggleSession(session.id)}
                      dense
                      selected={selected}
                      sx={{ borderRadius: 1, mb: 1 }}
                    >
                      <Checkbox edge="start" tabIndex={-1} disableRipple checked={selected} />
                      <ListItemText
                        primary={`Session ${session.id}${session.note ? ` — ${session.note}` : ''}`}
                        secondary={
                          <Stack direction="column" spacing={0.5}>
                            <span>Started {formatDateTime(session.started_at)}</span>
                            {session.instrument?.serial ? (
                              <span>Instrument {session.instrument.serial}</span>
                            ) : null}
                          </Stack>
                        }
                      />
                      <Stack spacing={1} direction="column" alignItems="flex-end">
                        {session.counts?.measurements ? (
                          <Chip size="small" label={`${session.counts.measurements} measurements`} />
                        ) : null}
                        {session.latest_measurement_at ? (
                          <Typography variant="caption" color="text.secondary">
                            Latest {formatDateTime(session.latest_measurement_at)}
                          </Typography>
                        ) : null}
                      </Stack>
                    </ListItemButton>
                  );
                })}
              </List>
            )}
          </CardContent>
        </Card>

        <Card sx={{ minHeight: 360 }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="subtitle1" fontWeight={600}>
                Overlay workspace
              </Typography>
              {evaluationLoading ? <CircularProgress size={20} /> : null}
            </Stack>
            {evaluationError ? (
              <Alert severity="error" sx={{ mb: 2 }}>
                {evaluationError.message}
              </Alert>
            ) : null}
            {!evaluations.length ? (
              <Box
                sx={{
                  borderRadius: 2,
                  border: '1px dashed',
                  borderColor: 'divider',
                  height: 260,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'text.secondary',
                  textAlign: 'center',
                  px: 2,
                }}
              >
                Select one or more sessions to render the overlay chart.
              </Box>
            ) : (
              <Box ref={chartRef} sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 16, right: 24, left: 8, bottom: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ddd" />
                    <XAxis
                      dataKey="offset_seconds"
                      tickFormatter={(value) => (typeof value === 'number' ? formatOffset(value) : String(value ?? ''))}
                      label={{ value: 'Time offset', position: 'insideBottom', offset: -10 }}
                    />
                    <YAxis
                      tickFormatter={(value: number) => value.toFixed(2)}
                      label={{ value: 'Measurement value', angle: -90, position: 'insideLeft' }}
                    />
                    <RechartsTooltip
                      formatter={(value: number, name: string) => [formatNumber(value), name.replace('session_', 'Session ')]}
                      labelFormatter={(value) => `Offset ${formatOffset(typeof value === 'number' ? value : Number(value))}`}
                    />
                    <Legend />
                    {evaluations.map((evaluation) => {
                      const color = colorBySession.get(evaluation.session.id) ?? '#1976d2';
                      return (
                        <Line
                          key={evaluation.session.id}
                          type="monotone"
                          dataKey={`session_${evaluation.session.id}`}
                          stroke={color}
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Statistics summary
          </Typography>
          {!evaluations.length ? (
            <Typography variant="body2" color="text.secondary">
              Summary metrics will appear once an overlay has been rendered.
            </Typography>
          ) : (
            <Stack spacing={2} divider={<Divider flexItem light />}>
              {evaluations.map((evaluation) => {
                const color = colorBySession.get(evaluation.session.id) ?? '#1976d2';
                return (
                  <Stack key={evaluation.session.id} spacing={1}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: color }} />
                        <Typography fontWeight={600}>
                          Session {evaluation.session.id}
                        </Typography>
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        Anchor {evaluation.anchor} • {evaluation.anchor_timestamp ? formatDateTime(evaluation.anchor_timestamp) : 'Unknown'}
                      </Typography>
                    </Stack>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Value ({evaluation.statistics.value.unit ?? '—'})
                        </Typography>
                        <Typography variant="body2">
                          Min {formatNumber(evaluation.statistics.value.min)} • Max {formatNumber(evaluation.statistics.value.max)} • Avg {formatNumber(evaluation.statistics.value.average)}
                        </Typography>
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Temperature ({evaluation.statistics.temperature.unit ?? '—'})
                        </Typography>
                        <Typography variant="body2">
                          Min {formatNumber(evaluation.statistics.temperature.min)} • Max {formatNumber(evaluation.statistics.temperature.max)} • Avg {formatNumber(evaluation.statistics.temperature.average)}
                        </Typography>
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Coverage
                        </Typography>
                        <Typography variant="body2">
                          Samples {evaluation.samples} • Span {formatDuration(evaluation.duration_seconds)}
                        </Typography>
                      </Box>
                    </Stack>
                  </Stack>
                );
              })}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Markers & notes
          </Typography>
          {!combinedMarkers.length ? (
            <Typography variant="body2" color="text.secondary">
              Calibration markers or notable events will appear here when detected in the overlay timeline.
            </Typography>
          ) : (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {combinedMarkers.map((marker, index) => (
                <Chip
                  key={`${marker.session_id}-${marker.measurement_id ?? index}`}
                  label={`Session ${marker.session_id} • ${marker.type} • ${formatOffset(marker.offset_seconds)}`}
                />
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
