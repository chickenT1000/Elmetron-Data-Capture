import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';
import AddLocationIcon from '@mui/icons-material/AddLocation';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import PersonIcon from '@mui/icons-material/Person';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import { useQueries, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis, ReferenceDot } from 'recharts';
import JSZip from 'jszip';
import { buildApiUrl } from '../config';
import type { MouseHandlerDataParam } from 'recharts';
import { toPng } from 'html-to-image';

import {
  addSessionMarker,
  deleteSession,
  deleteSessionMarker,
  downloadSessionEvaluationJson,
  fetchOperators,
  fetchSessionPage,
  fetchSessionMarkers,
  renameSession,
  type SessionEvaluationResponse,
  type SessionFilters,
  type SessionMarker,
  type SessionSummary,
  updateSessionOperator,
} from '../api/sessions';
import { sessionEvaluationQueryOptions } from '../hooks/useSessionEvaluation';

const COLOR_PALETTE = ['#1976d2', '#d81b60', '#2e7d32', '#f57c00', '#6d4c41', '#8e24aa'];

const formatDateTime = (value?: string | null): string => {
  if (!value) {
    return 'Unknown';
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
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
  const totalSeconds = Math.floor(Math.abs(value));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  // Format as HH:MM:SS
  const hh = hours.toString().padStart(2, '0');
  const mm = minutes.toString().padStart(2, '0');
  const ss = seconds.toString().padStart(2, '0');

  return `${hh}:${mm}:${ss}`;
};

const formatOffset = (value?: number | null): string => {
  if (value === undefined || value === null) {
    return '—';
  }
  // Round to nearest second (device sends 1 Hz data)
  const rounded = Math.round(value);
  const sign = rounded > 0 ? '+' : rounded < 0 ? '-' : '';
  const abs = Math.abs(rounded);

  if (abs >= 60) {
    const minutes = Math.floor(abs / 60);
    const seconds = abs % 60;
    return seconds > 0 ? `${sign}${minutes}m ${seconds}s` : `${sign}${minutes}m`;
  }
  return `${sign}${abs}s`;
};




const ANCHOR_OPTIONS = [
  { value: 'start', label: 'Align by session start' },
  { value: 'first_marker', label: 'Align by first marker' },
  { value: 'last_marker', label: 'Align by last marker' },
];

const buildFilename = (extension: string) => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return `session_evaluation_${timestamp}.${extension}`;
};


const isParameterMatch = (unit: string | null | undefined, parameter: 'ph' | 'redox' | 'conductivity'): boolean => {
  if (!unit) return false;
  const unitLower = unit.toLowerCase();

  switch (parameter) {
    case 'ph':
      return unitLower.includes('ph');
    case 'redox':
      return unitLower.includes('mv') || unitLower.includes('orp');
    case 'conductivity':
      return unitLower.includes('us') || unitLower.includes('ms') || unitLower.includes('s/cm') || unitLower.includes('siemens');
  }
};

const mergeSeriesForChart = (
  evaluations: SessionEvaluationResponse[],
  selectedParameter: 'ph' | 'redox' | 'conductivity',
  showTemperature: boolean
) => {
  const merged = new Map<string, Record<string, number | string>>();
  evaluations.forEach((evaluation) => {
    const valueKeyName = `session_${evaluation.session.id}`;
    const tempKeyName = `session_${evaluation.session.id}_temp`;

    evaluation.series.forEach((point, index) => {
      // Filter by selected parameter
      if (!isParameterMatch(point.unit, selectedParameter)) {
        return;
      }

      if (point.offset_seconds === null || point.offset_seconds == null) {
        const key = `idx_${evaluation.session.id}_${index}`;
        const bucket = merged.get(key) ?? { key: index, label: index };
        if (point.value !== null && point.value !== undefined) {
          bucket[valueKeyName] = point.value;
        }
        if (showTemperature && point.temperature !== null && point.temperature !== undefined) {
          bucket[tempKeyName] = point.temperature;
        }
        merged.set(key, bucket);
        return;
      }
      const key = point.offset_seconds.toFixed(3);
      const bucket = merged.get(key) ?? {
        offset_seconds: point.offset_seconds,
        offset_minutes: point.offset_seconds / 60,
      };
      if (point.value !== null && point.value !== undefined) {
        bucket[valueKeyName] = point.value;
      }
      if (showTemperature && point.temperature !== null && point.temperature !== undefined) {
        bucket[tempKeyName] = point.temperature;
      }
      merged.set(key, bucket);
    });
  });
  const result = Array.from(merged.values()).map((entry) => ({
    offset_seconds: typeof entry.offset_seconds === 'number' ? entry.offset_seconds : null,
    offset_minutes: typeof entry.offset_minutes === 'number' ? entry.offset_minutes : null,
    ...entry,
  }));
  result.sort((a, b) => {
    const leftKey = 'key' in a ? a.key : null;
    const rightKey = 'key' in b ? b.key : null;
    const left = typeof a.offset_seconds === 'number' ? a.offset_seconds : Number(leftKey ?? 0);
    const right = typeof b.offset_seconds === 'number' ? b.offset_seconds : Number(rightKey ?? 0);
    return left - right;
  });
  return result;
};


export default function SessionEvaluationPage() {
  // Version: 2025-10-30-14:00 - Marker fixes v3
  const queryClient = useQueryClient();
  const [anchor, setAnchor] = useState<'start' | 'first_marker' | 'last_marker'>('start');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [hiddenSessionIds, setHiddenSessionIds] = useState<Set<number>>(new Set());
  const [exportError, setExportError] = useState<string | null>(null);
  const [, setExportingPng] = useState(false);
  const chartRef = useRef<HTMLDivElement | null>(null);

  // Manual axis range control
  const [manualRangeEnabled, setManualRangeEnabled] = useState(false);
  const [manualXMin] = useState<number>(0);
  const [manualXMax] = useState<number>(0);
  const [manualYMin] = useState<number>(0);
  const [manualYMax] = useState<number>(0);

  // Filter state
  const [operatorFilter, setOperatorFilter] = useState<string>('');
  const [startDateFilter] = useState<Date | null>(null);
  const [endDateFilter] = useState<Date | null>(null);
  const [chartTypeFilter, setChartTypeFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'started_at' | 'measurement_count' | 'duration' | 'operator_name'>('started_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Session data
  const [cursor, setCursor] = useState(0);
  const [nextCursor, setNextCursor] = useState<number | null>(null);
  const requestNumber = useRef(0);
  useEffect(()=>setCursor(0),[operatorFilter,chartTypeFilter,sortBy,sortOrder]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  // Fetch operators list
  useQuery({
queryKey: ['operators'],
queryFn: fetchOperators,
staleTime: 60000, // Cache for 1 minute
});

  // Session selector


  // Chart parameter selection
  const [selectedParameter, setSelectedParameter] = useState<'ph' | 'redox' | 'conductivity'>('ph');
  const [showTemperature, setShowTemperature] = useState(false);

  // Marker placement mode
  const [markerPlacementMode, setMarkerPlacementMode] = useState(false);
  const [sessionForMarker, setSessionForMarker] = useState<number | null>(null);
  const [sessionMarkers, setSessionMarkers] = useState<Map<number, SessionMarker[]>>(new Map());
  const [markerDialogOpen, setMarkerDialogOpen] = useState(false);
  const [pendingMarker, setPendingMarker] = useState<{
    sessionId: number;
    timestamp: string;
    offset_seconds: number;
    offset_minutes: number;
    markerId?: number; // For editing existing markers
  } | null>(null);
  const [markerOffsetMinutes, setMarkerOffsetMinutes] = useState<number>(0); // For manual time adjustment


  // Dialog state
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [operatorDialogOpen, setOperatorDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToEdit, setSessionToEdit] = useState<number | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<number | null>(null);
  const [dialogLoading, setDialogLoading] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  // Refs for dialog inputs (to avoid re-renders on every keystroke)
  const renameInputRef = useRef<HTMLInputElement>(null);
  const operatorInputRef = useRef<HTMLInputElement>(null);
  const markerNoteInputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-disable manual range when sessions change
  useEffect(() => {
    setManualRangeEnabled(false);
  }, [selectedIds]);

  useEffect(() => {
    setMarkerPlacementMode(false);
    setSessionForMarker(null);
    setPendingMarker(null);
  }, [anchor, selectedParameter, showTemperature, selectedIds]);

  // Fetch sessions with filters
  const fetchSessions = useCallback(async () => {
    const request = ++requestNumber.current;
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const filters: SessionFilters = {
        limit: 50,
        cursor,
        sort_by: sortBy,
        order: sortOrder,
      };

      if (operatorFilter.trim()) {
        filters.operator = operatorFilter.trim();
      }

      if (startDateFilter) {
        filters.start_date = startDateFilter.toISOString();
      }

      if (endDateFilter) {
        filters.end_date = endDateFilter.toISOString();
      }

      if (chartTypeFilter === 'ph') {
        filters.has_ph = true;
      } else if (chartTypeFilter === 'redox') {
        filters.has_redox = true;
      } else if (chartTypeFilter === 'conductivity') {
        filters.has_conductivity = true;
      }

      const page = await fetchSessionPage(filters);
      if (request !== requestNumber.current) return;
      const data = page.sessions;
      setNextCursor(page.next_cursor);

      // For "most_data" filter, show only sessions with dominant parameter
      if (chartTypeFilter === 'most_data') {
        setSessions(data.filter(s => s.dominant_parameter && s.dominant_parameter !== 'none'));
      } else {
        setSessions(data);
      }
    } catch (error) {
      if (request !== requestNumber.current) return;
      setSessionsError(error instanceof Error ? error.message : 'Failed to fetch sessions');
      setSessions([]);
    } finally {
      if (request === requestNumber.current) setSessionsLoading(false);
    }
  }, [operatorFilter, startDateFilter, endDateFilter, chartTypeFilter, sortBy, sortOrder, cursor]);

  // Fetch sessions on mount and when filters change
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Fetch markers when selected sessions change
  useEffect(() => {
    const loadMarkers = async () => {
      const newMarkers = new Map<number, SessionMarker[]>();
      for (const sessionId of selectedIds) {
        try {
          const markers = await fetchSessionMarkers(sessionId);
          newMarkers.set(sessionId, markers);
        } catch (error) {
          console.error(`Failed to fetch markers for session ${sessionId}:`, error);
          newMarkers.set(sessionId, []);
        }
      }
      setSessionMarkers(newMarkers);
    };

    if (selectedIds.length > 0) {
      loadMarkers();
    }
  }, [selectedIds]);

  // Get available sessions (not already selected)

  // Get selected session objects

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

  // Filter out hidden sessions for chart display
  const visibleEvaluations = useMemo(
    () => evaluations.filter(e => !hiddenSessionIds.has(e.session.id)),
    [evaluations, hiddenSessionIds]
  );

  const chartData = useMemo(() => {
    let data = mergeSeriesForChart(visibleEvaluations, selectedParameter, showTemperature);

    // Filter data based on manual range or anchor mode
    if (manualRangeEnabled) {
      // Filter by manual X range, respecting anchor constraints
      let xMinSeconds = manualXMin * 60;
      let xMaxSeconds = manualXMax * 60;

      // Override based on anchor mode
      if (anchor === 'first_marker') {
        xMinSeconds = 0; // First marker always at 0
      } else if (anchor === 'last_marker') {
        xMaxSeconds = 0; // Last marker always at 0
      }

      data = data.filter(point => {
        if (point.offset_seconds == null) return true;
        return point.offset_seconds >= xMinSeconds && point.offset_seconds <= xMaxSeconds;
      });
    } else {
      // Filter by anchor mode
      if (anchor === 'first_marker') {
        // Only show data from first marker onwards (offset >= 0)
        data = data.filter(point => point.offset_seconds == null || point.offset_seconds >= 0);
      } else if (anchor === 'last_marker') {
        // Only show data up to last marker (offset <= 0)
        data = data.filter(point => point.offset_seconds == null || point.offset_seconds <= 0);
      }
    }


    return data;
  }, [visibleEvaluations, selectedParameter, showTemperature, anchor, manualRangeEnabled, manualXMin, manualXMax]);

  // Calculate time range for smart interval and X-axis domain
  const timeRange = useMemo(() => {
    // Use manual range if enabled, respecting anchor constraints
    if (manualRangeEnabled) {
      let min = manualXMin * 60;
      let max = manualXMax * 60;

      // Override based on anchor mode
      if (anchor === 'first_marker') {
        min = 0; // First marker always at 0
      } else if (anchor === 'last_marker') {
        max = 0; // Last marker always at 0
      }

      return { min, max };
    }

    let min = Infinity;
    let max = -Infinity;
    chartData.forEach(point => {
      if (point.offset_seconds != null && point.offset_seconds !== null) {
        if (point.offset_seconds < min) min = point.offset_seconds;
        if (point.offset_seconds > max) max = point.offset_seconds;
      }
    });

    // If no data, default to 0
    if (min === Infinity) min = 0;
    if (max === -Infinity) max = 0;

    // Adjust domain based on anchor mode
    if (anchor === 'start') {
      // Session start always at X=0
      min = 0;
    } else if (anchor === 'first_marker') {
      // First marker at X=0 (left edge) - only show data from marker onwards
      min = 0;
    } else if (anchor === 'last_marker') {
      // Last marker at X=0 (right edge) - only show data before marker
      max = 0;
    }


    return { min, max };
  }, [chartData, anchor, manualRangeEnabled, manualXMin, manualXMax]);


  // Calculate Y-axis domain from line data only (not markers) to keep scale stable
  const yAxisDomain = useMemo(() => {
    // Use manual range if enabled (check if values have been set, not just non-zero)
    if (manualRangeEnabled && (manualYMin !== manualYMax)) {
      return [manualYMin, manualYMax] as const;
    }

    let min = Infinity;
    let max = -Infinity;

    chartData.forEach(point => {
      visibleEvaluations.forEach(evaluation => {
        const value = (point as Record<string, number | string | null>)[`session_${evaluation.session.id}`];
        if (value !== undefined && value !== null && typeof value === 'number') {
          if (value < min) min = value;
          if (value > max) max = value;
        }
      });
    });

    if (min === Infinity || max === -Infinity) {
      return ['auto', 'auto'] as const;
    }

    // Add 5% padding to top and bottom
    const padding = (max - min) * 0.05;
    return [min - padding, max + padding] as const;
  }, [chartData, visibleEvaluations, manualRangeEnabled, manualYMin, manualYMax]);

  const colorBySession = useMemo(() => {
    const map = new Map<number, string>();
    evaluations.forEach((evaluation, index) => {
      const color = COLOR_PALETTE[index % COLOR_PALETTE.length];
      map.set(evaluation.session.id, color);
    });
    return map;
  }, [evaluations]);

  const combinedMarkers = useMemo(() => {
    const markers: Array<{ session_id: number; marker_number: number; offset_seconds: number; note?: string }> = [];

    // Use markers from evaluation responses (already adjusted for anchor mode)
    visibleEvaluations.forEach((evaluation) => {

      if (evaluation.markers) {
        evaluation.markers.forEach((marker) => {
          markers.push({
            session_id: evaluation.session.id,
            marker_number: marker.marker_number,
            offset_seconds: marker.offset_seconds,
            note: undefined
          });
        });
      }
    });


    return markers;
  }, [visibleEvaluations]);

  // Prepare marker scatter data for chart
  const markerScatterData = useMemo(() => {
    const data: Array<{
      session_id: number;
      marker_number: number;
      offset_minutes: number;
      value: number;
      color: string;
      note?: string;
    }> = [];

    // Use combinedMarkers which are already adjusted for anchor mode
    combinedMarkers.forEach((marker) => {
      const color = colorBySession.get(marker.session_id) ?? '#1976d2';

      // Find the value at this marker's time (closest data point)
      const markerMinutes = marker.offset_seconds / 60;
      const closestPoint = chartData.reduce((closest, point) => {
        if (point.offset_minutes == null) return closest;
        const diff = Math.abs(point.offset_minutes - markerMinutes);
        const value = (point as Record<string, number | string | null>)[`session_${marker.session_id}`];
        if (value !== undefined && value !== null) {
          if (!closest || diff < closest.diff) {
            return { point, diff, value: value as number };
          }
        }
        return closest;
      }, null as { point: Record<string, number | string | null>; diff: number; value: number } | null);

      if (closestPoint) {
        data.push({
          session_id: marker.session_id,
          marker_number: marker.marker_number,
          offset_minutes: markerMinutes,
          value: closestPoint.value,
          color,
          note: marker.note
        });
      }
    });

    return data;
  }, [combinedMarkers, chartData, colorBySession]);

  const evaluationLoading = evaluationQueries.some((query) => query.isLoading || query.isFetching);
  const evaluationError = evaluationQueries
    .map((query) => query.error)
    .find((error) => error instanceof Error) as Error | undefined;


  const handleRemoveSession = (sessionId: number) => {
    setSelectedIds(prev => prev.filter(id => id !== sessionId));
    setHiddenSessionIds(prev => {
      const newSet = new Set(prev);
      newSet.delete(sessionId);
      return newSet;
    });
  };

  const handleToggleVisibility = (sessionId: number) => {
    setHiddenSessionIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sessionId)) {
        newSet.delete(sessionId);
      } else {
        newSet.add(sessionId);
      }
      return newSet;
    });
  };

  const handleRenameOpen = (sessionId: number) => {
    const session = sessions.find(s => s.id === sessionId);
    setSessionToEdit(sessionId);
    setRenameDialogOpen(true);
    setDialogError(null);
    // Set initial value after dialog opens
    setTimeout(() => {
      if (renameInputRef.current) {
        renameInputRef.current.value = session?.note || '';
      }
    }, 0);
  };

  const handleOperatorOpen = (sessionId: number) => {
    const session = sessions.find(s => s.id === sessionId);
    setSessionToEdit(sessionId);
    setOperatorDialogOpen(true);
    setDialogError(null);
    // Set initial value after dialog opens
    setTimeout(() => {
      if (operatorInputRef.current) {
        operatorInputRef.current.value = session?.operator_name || '';
      }
    }, 0);
  };

  const handleDeleteOpen = (sessionId: number) => {
    setSessionToDelete(sessionId);
    setDeleteDialogOpen(true);
    setDialogError(null);
  };

  const handleRenameSubmit = async () => {
    const newName = renameInputRef.current?.value || '';
    if (!sessionToEdit || !newName.trim()) return;

    setDialogLoading(true);
    setDialogError(null);
    try {
      await renameSession(sessionToEdit, newName.trim());
      setRenameDialogOpen(false);
      await fetchSessions();
    } catch (error) {
      setDialogError(error instanceof Error ? error.message : 'Failed to rename session');
    } finally {
      setDialogLoading(false);
    }
  };

  const handleOperatorSubmit = async () => {
    if (!sessionToEdit) return;
    const newOperator = operatorInputRef.current?.value || '';

    setDialogLoading(true);
    setDialogError(null);
    try {
      await updateSessionOperator(sessionToEdit, newOperator.trim() || null);
      setOperatorDialogOpen(false);
      await fetchSessions();
    } catch (error) {
      setDialogError(error instanceof Error ? error.message : 'Failed to update operator');
    } finally {
      setDialogLoading(false);
    }
  };

  const handleDeleteSubmit = async () => {
    if (!sessionToDelete) return;

    setDialogLoading(true);
    setDialogError(null);
    try {
      await deleteSession(sessionToDelete);
      // Remove from selected sessions
      setSelectedIds(prev => prev.filter(id => id !== sessionToDelete));
      setHiddenSessionIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(sessionToDelete);
        return newSet;
      });
      setDeleteDialogOpen(false);
      setSessionToDelete(null);
      await fetchSessions();
    } catch (error) {
      setDialogError(error instanceof Error ? error.message : 'Failed to delete session');
    } finally {
      setDialogLoading(false);
    }
  };

  const handleStartMarkerPlacement = (sessionId: number) => {
    setMarkerPlacementMode(true);
    setSessionForMarker(sessionId);
  };

  const handleCancelMarkerPlacement = useCallback(() => {
    setMarkerPlacementMode(false);
    setSessionForMarker(null);
    setPendingMarker(null);
    setMarkerOffsetMinutes(0);

    if (markerNoteInputRef.current) {
      markerNoteInputRef.current.value = '';
    }
  }, []);


  const handleChartClick = (event: MouseHandlerDataParam) => {
    if (!markerPlacementMode || !sessionForMarker) return;
    const point = event.activeTooltipIndex == null ? undefined : chartData[Number(event.activeTooltipIndex)];
    if (point && point.offset_minutes != null) {
      const offset_minutes = point.offset_minutes;
      const chartOffset = point.offset_seconds ?? offset_minutes * 60;

      // Calculate timestamp
      const session = sessions.find(s => s.id === sessionForMarker);
      if (!session) {
        return;
      }

      const sessionStart = new Date(session.started_at);
      const evaluation = evaluations.find(e => e.session.id === sessionForMarker);
      const anchorTime = new Date(evaluation?.anchor_timestamp || session.started_at);
      const markerTime = new Date(anchorTime.getTime() + chartOffset * 1000);
      const offset_seconds = (markerTime.getTime() - sessionStart.getTime()) / 1000;

      setPendingMarker({
        sessionId: sessionForMarker,
        timestamp: markerTime.toISOString(),
        offset_seconds,
        offset_minutes: offset_seconds / 60
      });
      setMarkerOffsetMinutes(offset_seconds / 60);
      setMarkerDialogOpen(true);
    }
  };

  const handleConfirmMarker = async () => {
    if (!pendingMarker) return;
    const markerNote = markerNoteInputRef.current?.value || '';

    setDialogLoading(true);
    setDialogError(null);
    try {
      // Use manually adjusted time if changed
      const finalOffsetSeconds = markerOffsetMinutes * 60;
      const session = sessions.find(s => s.id === pendingMarker.sessionId);
      if (!session) return;

      const sessionStart = new Date(session.started_at);
      const finalTimestamp = new Date(sessionStart.getTime() + finalOffsetSeconds * 1000).toISOString();

      await addSessionMarker(
        pendingMarker.sessionId,
        finalTimestamp,
        finalOffsetSeconds,
        markerNote.trim() || undefined,
        pendingMarker.markerId
      );

      // Reload markers for this session
      const markers = await fetchSessionMarkers(pendingMarker.sessionId);
      setSessionMarkers(prev => new Map(prev).set(pendingMarker.sessionId, markers));

      // Refresh sessions list to update marker count
      await fetchSessions();

      // Invalidate evaluation query to refresh chart markers immediately
      queryClient.invalidateQueries({ queryKey: ['session-evaluation', pendingMarker.sessionId] });

      // Close dialogs and reset state
      setMarkerDialogOpen(false);
      setMarkerPlacementMode(false);
      setSessionForMarker(null);
      setPendingMarker(null);
      setMarkerOffsetMinutes(0);

      if (markerNoteInputRef.current) {
        markerNoteInputRef.current.value = '';
      }
    } catch (error) {
      setDialogError(error instanceof Error ? error.message : 'Failed to save marker');
    } finally {
      setDialogLoading(false);
    }
  };

  const handleEditMarker = (sessionId: number, marker: SessionMarker) => {
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;

    const sessionStart = new Date(session.started_at);
    const markerTime = new Date(sessionStart.getTime() + marker.offset_seconds * 1000);

    setPendingMarker({
      sessionId,
      timestamp: markerTime.toISOString(),
      offset_seconds: marker.offset_seconds,
      offset_minutes: marker.offset_seconds / 60,
      markerId: marker.id
    });
    setMarkerOffsetMinutes(marker.offset_seconds / 60);
    setMarkerDialogOpen(true);
    // Set initial value after dialog opens
    setTimeout(() => {
      if (markerNoteInputRef.current) {
        markerNoteInputRef.current.value = marker.note || '';
      }
    }, 0);
  };

  const handleDeleteMarker = async (sessionId: number, markerId: number) => {
    try {
      await deleteSessionMarker(sessionId, markerId);
      // Reload markers for this session
      const markers = await fetchSessionMarkers(sessionId);
      setSessionMarkers(prev => new Map(prev).set(sessionId, markers));

      // Refresh sessions list to update marker count
      await fetchSessions();

      // Invalidate evaluation query to refresh chart markers immediately
      queryClient.invalidateQueries({ queryKey: ['session-evaluation', sessionId] });
    } catch (error) {
      console.error('Failed to delete marker:', error);
    }
  };

  const downloadFullData = async (format: 'csv' | 'json') => {
    setExportError(null);
    try {
      const zip = new JSZip();
      let single: Blob | undefined;
      for (const id of selectedIds) {
        const response = await fetch(buildApiUrl(`/api/sessions/${id}/export?format=${format}`));
        if (!response.ok) throw new Error('Export failed: ' + response.status);
        single = await response.blob();
        zip.file(`session_${id}.${format}`,single);
      }
      if (!single) return;
      const link=document.createElement('a');
      const url=URL.createObjectURL(selectedIds.length===1 ? single : await zip.generateAsync({type:'blob'}));
      link.href=url;link.download=selectedIds.length===1 ? `session_${selectedIds[0]}.${format}` : buildFilename('zip');
      link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch (error) { setExportError(error instanceof Error ? error.message : String(error)); }
  };
  const handleExportJSON = () => downloadFullData('json');
  const handleExportCSV = () => downloadFullData('csv');

  const handleExportPNG = async () => {
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
    <Stack spacing={3} sx={{ pb: 3 }}>
      {exportError ? (
        <Alert severity="error" onClose={() => setExportError(null)}>
          {exportError}
        </Alert>
      ) : null}

      {/* Workspace Card - Full Width */}
      <Card sx={{ minHeight: 360 }}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="subtitle1" fontWeight={600}>
              Workspace
            </Typography>
            {evaluationLoading ? <CircularProgress size={20} /> : null}
          </Stack>

          {/* Parameter Selector */}
          <Stack direction="row" spacing={0} alignItems="center" sx={{ flexWrap: 'wrap', gap: 2 }} mb={2}>
            <ToggleButtonGroup
              value={selectedParameter}
              exclusive
              onChange={(_, value) => value && setSelectedParameter(value)}
              size="small"
              sx={{ '& .MuiToggleButton-root': { textTransform: 'none' } }}
            >
              <ToggleButton value="ph">pH</ToggleButton>
              <ToggleButton value="redox">Redox</ToggleButton>
              <ToggleButton value="conductivity">Conductivity</ToggleButton>
            </ToggleButtonGroup>

            {/* Visual separator for standalone feature */}
            <Box sx={{ width: 16 }} />

            <ToggleButtonGroup
              value={showTemperature ? ['temperature'] : []}
              onChange={(_, value) => setShowTemperature(value.includes('temperature'))}
              size="small"
              sx={{ '& .MuiToggleButton-root': { textTransform: 'none' } }}
            >
              <ToggleButton value="temperature">Temperature</ToggleButton>
            </ToggleButtonGroup>

            <Box sx={{ flexGrow: 1 }} />

            <TextField size="small" sx={{ minWidth: 160 }} label="Operator filter" value={operatorFilter} onChange={e=>setOperatorFilter(e.target.value)} />
            <Select size="small" value={chartTypeFilter} onChange={e=>setChartTypeFilter(e.target.value)} inputProps={{'aria-label':'Parameter filter'}}>
              {['all','ph','redox','conductivity'].map(p=><MenuItem key={p} value={p}>{p}</MenuItem>)}
            </Select>
            {evaluations.some(e=>e.samples>e.series.length) && <Alert severity="info">Chart is sampled. CSV / JSON exports include every measurement.</Alert>}
            {/* Alignment & Export Controls */}
            <Stack direction="row" spacing={0} alignItems="center" sx={{ flexWrap: 'wrap', gap: 2 }}>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="anchor-select">Workspace Alignment</InputLabel>
                <Select
                  labelId="anchor-select"
                  value={anchor}
                  label="Workspace Alignment"
                  onChange={(event) => setAnchor(event.target.value as 'start' | 'first_marker' | 'last_marker')}
                >
                  {ANCHOR_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="export-select" shrink>Export</InputLabel>
                <Select
                  labelId="export-select"
                  value=""
                  label="Export"
                  displayEmpty
                  notched
                  renderValue={() => 'Select data'}
                >
                  <MenuItem onClick={handleExportPNG}>Export as PNG</MenuItem>
                  <MenuItem onClick={handleExportCSV}>Export as CSV</MenuItem>
                  <MenuItem onClick={handleExportJSON}>Export as JSON</MenuItem>
                  <MenuItem onClick={handleDownloadSessionJson} disabled={!selectedIds.length}>
                    Export session JSON
                  </MenuItem>
                </Select>
              </FormControl>
            </Stack>
          </Stack>

          {/* Chart */}
          {evaluationLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
              <CircularProgress />
            </Box>
          ) : evaluationError ? (
            <Alert severity="error">{evaluationError.message}</Alert>
          ) : chartData.length === 0 ? (
            <Alert severity="info">
              No data to display. Select sessions and parameters to visualize measurements.
            </Alert>
          ) : (
            <Box ref={chartRef} sx={{ width: '100%', height: 500 }}>
              <ResponsiveContainer>
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  onClick={markerPlacementMode ? handleChartClick : undefined}
                  style={markerPlacementMode ? { cursor: 'crosshair' } : undefined}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="offset_minutes"
                    type="number"
                    domain={[timeRange.min / 60, timeRange.max / 60]}
                    tickFormatter={(value: number) => formatOffset(value * 60)}
                    label={{
                      value: anchor === 'start'
                        ? 'Time from session start (min)'
                        : anchor === 'first_marker'
                        ? 'Time from first marker (min)'
                        : 'Time from last marker (min)',
                      position: 'insideBottom',
                      offset: -15,
                      style: { fontSize: 14 }
                    }}
                  />
                  <YAxis
                    yAxisId="left"
                    domain={yAxisDomain}
                    tickFormatter={(value: number) => value.toFixed(2)}
                    label={{
                      value: selectedParameter === 'ph' ? 'pH' : selectedParameter === 'redox' ? 'Redox (mV)' : 'Conductivity (µS/cm)',
                      angle: -90,
                      position: 'insideLeft',
                      offset: 10,
                      style: { fontSize: 14, textAnchor: 'middle' }
                    }}
                  />
                  {showTemperature && (
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tickFormatter={(value: number) => value.toFixed(1)}
                      label={{
                        value: 'Temperature (°C)',
                        angle: 90,
                        position: 'insideRight',
                        offset: 10,
                        style: { fontSize: 14, textAnchor: 'middle' }
                      }}
                    />
                  )}
                  <RechartsTooltip
                    formatter={(value: number, name: string) => {
                      if (!name || typeof name !== 'string') return [formatNumber(value), 'Value'];
                      const isTemp = name.includes('_temp');
                      const sessionName = name.replace('session_', 'Session ').replace('_temp', '');
                      return [
                        `${formatNumber(value)}${isTemp ? ' °C' : ''}`,
                        isTemp ? `${sessionName} (Temp)` : sessionName
                      ];
                    }}
                    labelFormatter={(value) => `Time: ${typeof value === 'number' ? value.toFixed(1) : value} min`}
                  />
                  {visibleEvaluations.map((evaluation) => {
                    const color = colorBySession.get(evaluation.session.id) ?? '#1976d2';
                    const isTargetSession = evaluation.session.id === sessionForMarker;
                    const opacity = markerPlacementMode && !isTargetSession ? 0.2 : 1;

                    return (
                      <Line
                        key={evaluation.session.id}
                        yAxisId="left"
                        type="monotone"
                        dataKey={`session_${evaluation.session.id}`}
                        name={`Session ${evaluation.session.id}`}
                        stroke={color}
                        strokeWidth={2}
                        strokeOpacity={opacity}
                        dot={false}
                        isAnimationActive={false}
                      />
                    );
                  })}
                  {showTemperature && visibleEvaluations.map((evaluation) => {
                    const color = colorBySession.get(evaluation.session.id) ?? '#1976d2';
                    const isTargetSession = evaluation.session.id === sessionForMarker;
                    const opacity = markerPlacementMode && !isTargetSession ? 0.2 : 1;

                    return (
                      <Line
                        key={`${evaluation.session.id}_temp`}
                        yAxisId="right"
                        type="monotone"
                        dataKey={`session_${evaluation.session.id}_temp`}
                        name={`Session ${evaluation.session.id} (Temp)`}
                        stroke={color}
                        strokeWidth={1}
                        strokeOpacity={opacity}
                        strokeDasharray="5 5"
                        dot={false}
                        isAnimationActive={false}
                      />
                    );
                  })}
                  {markerScatterData.map((marker) => (
                    <ReferenceDot
                      key={`marker-${marker.session_id}-${marker.marker_number}`}
                      x={marker.offset_minutes}
                      y={marker.value}
                      yAxisId="left"
                      r={12}
                      fill="#fff"
                      stroke={marker.color}
                      strokeWidth={2.5}
                      ifOverflow="extendDomain"
                      shape={(props: { cx?: number; cy?: number }) => {
                        const { cx, cy } = props;
                        if (cx == null || cy == null) return <g />;
                        return (
                          <g>
                            <circle
                              cx={cx}
                              cy={cy}
                              r={12}
                              fill="#fff"
                              stroke={marker.color}
                              strokeWidth={2.5}
                              style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))', pointerEvents: 'none' }}
                            />
                            <text
                              x={cx}
                              y={cy}
                              textAnchor="middle"
                              dominantBaseline="central"
                              fill={marker.color}
                              fontSize={11}
                              fontWeight="bold"
                              style={{ pointerEvents: 'none' }}
                            >
                              {marker.marker_number}
                            </text>
                          </g>
                        );
                      }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Marker Placement Mode Banner */}
      {markerPlacementMode && (
        <Alert
          severity="info"
          action={
            <Button color="inherit" size="small" onClick={handleCancelMarkerPlacement}>
              Cancel
            </Button>
          }
        >
          Click on the chart to place a marker for <strong>Session {sessionForMarker}</strong>
        </Alert>
      )}

      {/* Saved Sessions Table */}
      <Card>
          <CardContent sx={{overflowX: 'auto'}}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Saved Sessions
            </Typography>

            <Stack direction="row" spacing={2} sx={{my:1}}>
              <Button disabled={cursor===0 || sessionsLoading} onClick={()=>setCursor(Math.max(0,cursor-50))}>Previous page</Button>
              <Typography sx={{alignSelf:'center'}}>Page {Math.floor(cursor/50)+1}</Typography>
              <Button disabled={nextCursor==null || sessionsLoading} onClick={()=>setCursor(nextCursor ?? 0)}>Next page</Button>
            </Stack>
            {/* Sessions List - Simple checkbox list */}
            {sessionsLoading ? (
              <Stack alignItems="center" py={4} spacing={1}>
                <CircularProgress size={32} />
                <Typography variant="body2" color="text.secondary">
                  Loading sessions...
                </Typography>
              </Stack>
            ) : sessionsError ? (
              <Alert severity="error">{sessionsError}</Alert>
            ) : sessions.length === 0 ? (
              <Alert severity="info">No sessions available</Alert>
            ) : (
              <>
                {/* Table Header */}
                <Box
                  sx={{
                    display: 'grid',
                    minWidth: 1200,
                    gridTemplateColumns: '60px 180px 60px 180px 120px 100px 100px 80px 80px',
                    gap: 2,
                    alignItems: 'center',
                    py: 1,
                    borderBottom: 1,
                    borderColor: 'divider',
                    mb: 1,
                  }}
                >
                  <Typography variant="caption" fontWeight={600} color="text.secondary">
                    Workspace
                  </Typography>
                    <Typography variant="caption" fontWeight={600} color="text.secondary">
                      Session Name
                    </Typography>
                    <Typography variant="caption" fontWeight={600} color="text.secondary" textAlign="center">
                      ID
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, cursor: 'pointer' }} onClick={() => {
                      const newOrder = sortBy === 'started_at' && sortOrder === 'asc' ? 'desc' : 'asc';
                      setSortBy('started_at');
                      setSortOrder(newOrder);
                    }}>
                      <Typography variant="caption" fontWeight={600} color="text.secondary">
                        Date & Time
                      </Typography>
                      {sortBy === 'started_at' && (sortOrder === 'asc' ? <ArrowUpwardIcon sx={{ fontSize: 14 }} /> : <ArrowDownwardIcon sx={{ fontSize: 14 }} />)}
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, cursor: 'pointer' }} onClick={() => {
                      const newOrder = sortBy === 'operator_name' && sortOrder === 'asc' ? 'desc' : 'asc';
                      setSortBy('operator_name');
                      setSortOrder(newOrder);
                    }}>
                      <Typography variant="caption" fontWeight={600} color="text.secondary">
                        Operator
                      </Typography>
                      {sortBy === 'operator_name' && (sortOrder === 'asc' ? <ArrowUpwardIcon sx={{ fontSize: 14 }} /> : <ArrowDownwardIcon sx={{ fontSize: 14 }} />)}
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, cursor: 'pointer' }} onClick={() => {
                      const newOrder = sortBy === 'duration' && sortOrder === 'asc' ? 'desc' : 'asc';
                      setSortBy('duration');
                      setSortOrder(newOrder);
                    }}>
                      <Typography variant="caption" fontWeight={600} color="text.secondary">
                        Duration
                      </Typography>
                      {sortBy === 'duration' && (sortOrder === 'asc' ? <ArrowUpwardIcon sx={{ fontSize: 14 }} /> : <ArrowDownwardIcon sx={{ fontSize: 14 }} />)}
                    </Box>
                    <Typography variant="caption" fontWeight={600} color="text.secondary" textAlign="center">
                      Main Parameter
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, cursor: 'pointer' }} onClick={() => {
                      const newOrder = sortBy === 'measurement_count' && sortOrder === 'asc' ? 'desc' : 'asc';
                      setSortBy('measurement_count');
                      setSortOrder(newOrder);
                    }}>
                      <Typography variant="caption" fontWeight={600} color="text.secondary">
                        Data Points
                      </Typography>
                      {sortBy === 'measurement_count' && (sortOrder === 'asc' ? <ArrowUpwardIcon sx={{ fontSize: 14 }} /> : <ArrowDownwardIcon sx={{ fontSize: 14 }} />)}
                    </Box>
                    <Typography variant="caption" fontWeight={600} color="text.secondary" textAlign="center">
                      Markers
                    </Typography>
                </Box>

                <Stack spacing={0.5}>
                  {sessions.map((session) => {
                  const isSelected = selectedIds.includes(session.id);
                  const isHidden = hiddenSessionIds.has(session.id);
                  const color = colorBySession.get(session.id) ?? '#1976d2';
                  // Use calculated_ended_at for duration if ended_at is not available
                  const endTime = session.ended_at || session.calculated_ended_at;
                  const duration = endTime
                    ? (new Date(endTime).getTime() - new Date(session.started_at).getTime()) / 1000
                    : null;

                  return (
                    <Box key={session.id}>
                      {/* Session Row */}
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          py: 0.5,
                          '&:hover': {
                            bgcolor: 'action.hover',
                          },
                          borderRadius: 1,
                        }}
                      >
                        <Box
                          sx={{
                            flex: 1,
                            display: 'grid',
                            minWidth: 1200,
                    gridTemplateColumns: '60px 180px 60px 180px 120px 100px 100px 80px 80px',
                            gap: 2,
                            alignItems: 'center',
                          }}
                        >
                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 0.5 }}>
                          <Checkbox
                            checked={isSelected}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedIds(prev => [...prev, session.id]);
                                // Auto-select the session's dominant parameter
                                if (session.dominant_parameter && session.dominant_parameter !== 'none') {
                                  setSelectedParameter(session.dominant_parameter as 'ph' | 'redox' | 'conductivity');
                                }
                              } else {
                                handleRemoveSession(session.id);
                              }
                            }}
                          />
                          {isSelected && (
                            <Box
                              sx={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                backgroundColor: color,
                                opacity: isHidden ? 0.3 : 1
                              }}
                            />
                          )}
                        </Box>
                          <Typography variant="body2" fontWeight={500} sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '180px' }}>
                            {session.note || `Session ${session.id}`}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center">
                            {session.id}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {formatDateTime(session.started_at)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {session.operator_name || '—'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center">
                            {duration !== null ? formatDuration(duration) : 'Ongoing'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center">
                            {session.dominant_parameter && session.dominant_parameter !== 'none' ? session.dominant_parameter : '—'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center">
                            {session.counts?.measurements || 0}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" textAlign="center">
                            {session.counts?.markers || 0}
                          </Typography>
                        </Box>
                        <Stack direction="row" spacing={0.5} sx={{ ml: 1 }}>
                          {isSelected && (
                            <>
                              <Tooltip title={isHidden ? 'Show in chart' : 'Hide from chart'}>
                                <IconButton
                                  size="small"
                                  onClick={() => handleToggleVisibility(session.id)}
                                >
                                  {isHidden ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Add marker">
                                <IconButton
                                  size="small"
                                  onClick={() => handleStartMarkerPlacement(session.id)}
                                  disabled={markerPlacementMode}
                                >
                                  <AddLocationIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                          <Tooltip title="Rename session">
                            <IconButton
                              size="small"
                              onClick={() => handleRenameOpen(session.id)}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit operator">
                            <IconButton
                              size="small"
                              onClick={() => handleOperatorOpen(session.id)}
                            >
                              <PersonIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete session">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteOpen(session.id)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </Box>

                      {/* Marker Rows - Only show if session is selected */}
                      {isSelected && sessionMarkers.get(session.id) && sessionMarkers.get(session.id)!.length > 0 && (
                        <Box sx={{ ml: 8, mt: 0.5, mb: 0.5 }}>
                          {sessionMarkers.get(session.id)!.map((marker) => (
                            <Box
                              key={marker.id}
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                p: 1,
                                mb: 0.5,
                                borderRadius: 1,
                                borderLeft: `3px solid ${color}`
                              }}
                            >
                              <Typography variant="caption" flex={1}>
                                <strong>Marker {marker.marker_number}:</strong> {formatOffset(marker.offset_seconds)}
                                {marker.note && ` - ${marker.note}`}
                              </Typography>
                              <Stack direction="row" spacing={0.5}>
                                <IconButton
                                  size="small"
                                  onClick={() => handleEditMarker(session.id, marker)}
                                  title="Edit marker"
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                                <IconButton
                                  size="small"
                                  onClick={() => handleDeleteMarker(session.id, marker.id)}
                                  title="Delete marker"
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Stack>
                            </Box>
                          ))}
                        </Box>
                      )}
                    </Box>
                  );
                })}
                </Stack>
              </>
            )}
          </CardContent>
        </Card>

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onClose={() => !dialogLoading && setRenameDialogOpen(false)}>
        <DialogTitle>Rename Session</DialogTitle>
        <DialogContent>
          {dialogError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {dialogError}
            </Alert>
          )}
          <TextField
            autoFocus
            fullWidth
            label="Session Name"
            inputRef={renameInputRef}
            defaultValue=""
            disabled={dialogLoading}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)} disabled={dialogLoading}>
            Cancel
          </Button>
          <Button onClick={handleRenameSubmit} variant="contained" disabled={dialogLoading}>
            {dialogLoading ? <CircularProgress size={24} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Operator Dialog */}
      <Dialog open={operatorDialogOpen} onClose={() => !dialogLoading && setOperatorDialogOpen(false)}>
        <DialogTitle>Edit Operator</DialogTitle>
        <DialogContent>
          {dialogError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {dialogError}
            </Alert>
          )}
          <TextField
            autoFocus
            fullWidth
            label="Operator Name"
            inputRef={operatorInputRef}
            defaultValue=""
            disabled={dialogLoading}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOperatorDialogOpen(false)} disabled={dialogLoading}>
            Cancel
          </Button>
          <Button onClick={handleOperatorSubmit} variant="contained" disabled={dialogLoading}>
            {dialogLoading ? <CircularProgress size={24} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => !dialogLoading && setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Session</DialogTitle>
        <DialogContent>
          {dialogError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {dialogError}
            </Alert>
          )}
          <Typography>
            Are you sure you want to delete this session? This will remove all measurements, markers, and metadata.
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={dialogLoading}>
            Cancel
          </Button>
          <Button onClick={handleDeleteSubmit} color="error" variant="contained" disabled={dialogLoading}>
            {dialogLoading ? <CircularProgress size={24} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Marker Placement Dialog */}
      <Dialog open={markerDialogOpen} onClose={() => !dialogLoading && setMarkerDialogOpen(false)}>
        <DialogTitle>{pendingMarker?.markerId ? 'Edit Marker' : 'Add Marker'}</DialogTitle>
        <DialogContent>
          {dialogError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {dialogError}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Marker Note (optional)"
            inputRef={markerNoteInputRef}
            defaultValue=""
            disabled={dialogLoading}
            multiline
            rows={3}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMarkerDialogOpen(false)} disabled={dialogLoading}>
            Cancel
          </Button>
          <Button onClick={handleConfirmMarker} variant="contained" disabled={dialogLoading}>
            {dialogLoading ? <CircularProgress size={24} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
