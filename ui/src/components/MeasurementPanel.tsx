import React, { useState, useEffect } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Slider,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import AddLocationIcon from '@mui/icons-material/AddLocation';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SensorsIcon from '@mui/icons-material/Sensors';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import Switch from '@mui/material/Switch';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
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
  recordingEnabled?: boolean;
  onRecordingToggle?: () => void;
  isLiveMode?: boolean;
  chartTimeRangeIndex?: number;
  onChartTimeRangeChange?: (index: number) => void;
  timeRangeOptions?: number[];
}

// Session edit mode type
type SessionEditMode = 'none' | 'renaming' | 'creating';

interface SessionEditState {
  mode: SessionEditMode;
  editValue: string;
  loading: boolean;
  error: string | null;
}

export const MeasurementPanel: React.FC<MeasurementPanelProps> = ({ 
  state, 
  metrics, 
  recordingEnabled, 
  onRecordingToggle, 
  isLiveMode,
  chartTimeRangeIndex = 2,
  onChartTimeRangeChange,
  timeRangeOptions = [1, 5, 10, 20, 30, 60, 120]
}) => {
  // Current session data - fetched from API
  const [currentSession, setCurrentSession] = useState({
    id: null as number | null,
    session_number: null as number | null,
    name: null as string | null,
    display_name: 'Loading...',
    started_at: null as string | null,
    ended_at: null as string | null,
    operator_name: null as string | null,
  });
  
  // Session editing state
  const [editState, setEditState] = useState<SessionEditState>({
    mode: 'none',
    editValue: '',
    loading: false,
    error: null,
  });
  
  // Stop recording confirmation state
  const [stopConfirmPending, setStopConfirmPending] = useState(false);
  
  // Marker dialog state
  const [markerDialogOpen, setMarkerDialogOpen] = useState(false);
  const [markerNote, setMarkerNote] = useState('');
  const [markerOffsetSeconds, setMarkerOffsetSeconds] = useState(0);
  const [markerLoading, setMarkerLoading] = useState(false);
  const [markerError, setMarkerError] = useState<string | null>(null);
  const [editingMarkerId, setEditingMarkerId] = useState<number | null>(null);
  const [sessionMarkers, setSessionMarkers] = useState<Array<{
    id: number;
    marker_number: number;
    offset_seconds: number;
    note: string | null;
  }>>([]);

  // Force re-render every second to update session duration
  const [, forceUpdate] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      forceUpdate(n => n + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch current session ID from API
  useEffect(() => {
    const fetchCurrentSession = async () => {
      try {
        const response = await fetch('http://localhost:8050/api/live/status');
        const data = await response.json();
        
        if (data.current_session_id) {
          // Fetch session details to get the name and operator
          const sessionResponse = await fetch(`http://localhost:8050/api/sessions/${data.current_session_id}`);
          const sessionData = await sessionResponse.json();
          
          setCurrentSession({
            id: sessionData.id,
            session_number: sessionData.id, // Using ID as session number for now
            name: sessionData.note,
            display_name: sessionData.note || `Session ${sessionData.id}`,
            started_at: sessionData.started_at,
            ended_at: sessionData.ended_at,
            operator_name: sessionData.operator_name,
          });
        } else {
          // No active session
          setCurrentSession({
            id: null,
            session_number: null,
            name: null,
            display_name: 'No active session',
            started_at: null,
            ended_at: null,
            operator_name: null,
          });
        }
      } catch (error) {
        console.error('[ERROR] Failed to fetch current session:', error);
        toast.error('Failed to load session information');
      }
    };

    fetchCurrentSession();
    // Poll every 5 seconds to keep session info fresh
    const interval = setInterval(fetchCurrentSession, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch markers for current session
  useEffect(() => {
    const fetchMarkers = async () => {
      if (!currentSession.id) {
        setSessionMarkers([]);
        return;
      }
      
      try {
        const { fetchSessionMarkers } = await import('../api/sessions');
        const markers = await fetchSessionMarkers(currentSession.id);
        setSessionMarkers(markers);
      } catch (error) {
        console.error('Failed to fetch markers:', error);
      }
    };
    
    fetchMarkers();
  }, [currentSession.id]);

  // Validation: sanitize and validate session name
  const validateSessionName = (name: string): { valid: boolean; error: string | null; sanitized: string } => {
    const sanitized = name.trim().replace(/[<>:"/\\|?*]/g, '');
    
    if (sanitized.length === 0) {
      return { valid: false, error: 'Session name cannot be empty', sanitized };
    }
    
    if (sanitized.length > 50) {
      return { valid: false, error: 'Session name must be 50 characters or less', sanitized: sanitized.substring(0, 50) };
    }
    
    // TODO: Check uniqueness against backend
    // For now, just validate locally
    
    return { valid: true, error: null, sanitized };
  };

  // Handle clicking "Rename Current Session" button
  const handleRenameClick = () => {
    setEditState({
      mode: 'renaming',
      editValue: currentSession.name || `Session ${currentSession.session_number}`,
      loading: false,
      error: null,
    });
  };

  // Handle clicking "Start New Session" button
  const handleNewSessionClick = async () => {
    // Set loading state while fetching next number
    setEditState({
      mode: 'creating',
      editValue: '',
      loading: true,
      error: null,
    });

    // TODO: Fetch next session number from API
    // Mockup: simulate API call
    setTimeout(() => {
      const nextNumber = currentSession.session_number + 1;
      console.log('[MOCKUP] Fetched next session number:', nextNumber);
      
      setEditState({
        mode: 'creating',
        editValue: `Session ${nextNumber}`,
        loading: false,
        error: null,
      });
    }, 300);
  };

  // Handle confirming rename
  const handleRenameConfirm = async () => {
    const validation = validateSessionName(editState.editValue);
    
    if (!validation.valid) {
      setEditState(prev => ({ ...prev, error: validation.error }));
      return;
    }

    setEditState(prev => ({ ...prev, loading: true, error: null }));

    try {
      // API call to rename session
      const response = await fetch(`http://localhost:8050/api/sessions/${currentSession.id}/rename`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: validation.sanitized }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to rename session');
      }

      const result = await response.json();
      console.log('[SUCCESS] Session renamed:', result);
      
      // Update local state with new name
      setCurrentSession(prev => ({ 
        ...prev, 
        name: validation.sanitized,
        display_name: validation.sanitized
      }));
      setEditState({ mode: 'none', editValue: '', loading: false, error: null });
      
      // Show success toast
      toast.success(`Session renamed to "${validation.sanitized}"`, {
        position: 'bottom-right',
        autoClose: 3000,
      });
    } catch (error) {
      console.error('[ERROR] Failed to rename session:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to rename session';
      
      setEditState(prev => ({ 
        ...prev, 
        loading: false, 
        error: errorMessage
      }));
      
      // Show error toast
      toast.error(errorMessage, {
        position: 'bottom-right',
        autoClose: 5000,
      });
    }
  };

  // Handle confirming new session
  const handleNewSessionConfirm = async () => {
    const validation = validateSessionName(editState.editValue);
    
    if (!validation.valid) {
      setEditState(prev => ({ ...prev, error: validation.error }));
      return;
    }

    setEditState(prev => ({ ...prev, loading: true, error: null }));

    // TODO: API call to create new session
    console.log('[MOCKUP] Create new session with name:', validation.sanitized);
    
    // Simulate API call
    setTimeout(() => {
      console.log('[MOCKUP] New session created successfully');
      setEditState({ mode: 'none', editValue: '', loading: false, error: null });
      // TODO: Show success toast
      // TODO: Refresh current session data
      // TODO: Update charts with new session
    }, 500);
  };

  // Handle canceling edit
  const handleEditCancel = () => {
    setEditState({ mode: 'none', editValue: '', loading: false, error: null });
  };

  // Handle adding marker
  const handleAddMarkerClick = () => {
    if (!currentSession.id || !currentSession.started_at) {
      toast.error('No active session');
      return;
    }
    setEditingMarkerId(null);
    setMarkerNote('');
    // Calculate current offset for new marker
    const now = new Date();
    const sessionStart = new Date(currentSession.started_at);
    const offsetSeconds = Math.floor((now.getTime() - sessionStart.getTime()) / 1000);
    setMarkerOffsetSeconds(offsetSeconds);
    setMarkerError(null);
    setMarkerDialogOpen(true);
  };

  const handleEditMarkerClick = (marker: { id: number; offset_seconds: number; note: string | null }) => {
    setEditingMarkerId(marker.id);
    setMarkerNote(marker.note || '');
    setMarkerOffsetSeconds(marker.offset_seconds);
    setMarkerError(null);
    setMarkerDialogOpen(true);
  };

  const handleMarkerConfirm = async () => {
    if (!currentSession.id || !currentSession.started_at) {
      setMarkerError('No active session');
      return;
    }

    // Validate offset
    if (markerOffsetSeconds < 0) {
      setMarkerError('Marker time cannot be before session start');
      return;
    }

    setMarkerLoading(true);
    setMarkerError(null);

    try {
      if (editingMarkerId) {
        // Update existing marker
        const { updateSessionMarker } = await import('../api/sessions');
        await updateSessionMarker(currentSession.id, editingMarkerId, markerOffsetSeconds, markerNote || null);
        toast.success('Marker updated successfully', {
          position: 'bottom-right',
          autoClose: 2000,
        });
      } else {
        // Create marker
        const { createSessionMarker } = await import('../api/sessions');
        await createSessionMarker(currentSession.id, markerOffsetSeconds, markerNote || null);
        toast.success('Marker added successfully', {
          position: 'bottom-right',
          autoClose: 2000,
        });
      }

      // Refresh markers
      const { fetchSessionMarkers } = await import('../api/sessions');
      const markers = await fetchSessionMarkers(currentSession.id);
      setSessionMarkers(markers);

      setMarkerDialogOpen(false);
      setMarkerNote('');
      setMarkerOffsetSeconds(0);
      setEditingMarkerId(null);
    } catch (error) {
      console.error('Failed to save marker:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to save marker';
      setMarkerError(errorMessage);
      toast.error(errorMessage, {
        position: 'bottom-right',
        autoClose: 5000,
      });
    } finally {
      setMarkerLoading(false);
    }
  };

  const handleMarkerCancel = () => {
    setMarkerDialogOpen(false);
    setMarkerNote('');
    setMarkerOffsetSeconds(0);
    setMarkerError(null);
    setEditingMarkerId(null);
  };

  const handleDeleteMarker = async (markerId: number) => {
    if (!currentSession.id) return;

    try {
      const { deleteSessionMarker } = await import('../api/sessions');
      await deleteSessionMarker(currentSession.id, markerId);

      // Refresh markers
      const { fetchSessionMarkers } = await import('../api/sessions');
      const markers = await fetchSessionMarkers(currentSession.id);
      setSessionMarkers(markers);

      toast.success('Marker deleted', {
        position: 'bottom-right',
        autoClose: 2000,
      });
    } catch (error) {
      console.error('Failed to delete marker:', error);
      toast.error('Failed to delete marker', {
        position: 'bottom-right',
        autoClose: 5000,
      });
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !editState.loading) {
      e.preventDefault();
      if (editState.mode === 'renaming') {
        handleRenameConfirm();
      } else if (editState.mode === 'creating') {
        handleNewSessionConfirm();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleEditCancel();
    }
  };

  const handleTimeRangeChange = (_event: Event, value: number | number[]) => {
    const newIndex = Array.isArray(value) ? value[0] : value;
    if (onChartTimeRangeChange) {
      onChartTimeRangeChange(newIndex);
    }
  };

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

  return (
    <>
      <ToastContainer />
      <Stack spacing={2}>
        {isTimeMode && (
          <Alert severity="info">
            <Typography variant="body2">
              <strong>Device in TIME mode:</strong> The meter is currently displaying time and is not sending measurement data. 
              Switch the device to measurement mode to resume data collection.
            </Typography>
          </Alert>
        )}

      <Box sx={{ display: 'flex', gap: 3 }}>
        {/* Left Card: Measurements */}
        <Card sx={{ flex: 1.618, minWidth: 0 }}>
          <CardContent>
            {/* Header: Session Name */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Current session: {currentSession.display_name}
              </Typography>
            </Box>

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
              <Stack spacing={3}>
                {/* Main measurement (pH/Redox/Conductivity) */}
                <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
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

                {/* Temperature (second row) */}
                <Box sx={{ display: 'flex', flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
                  <Typography variant="h5" color="text.secondary" fontWeight={500} sx={{ display: 'inline-block', width: 140 }}>
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

                {/* Session Metadata (below measurements) */}
                {currentSession.started_at && (
                  <Stack spacing={0.5} sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary">
                      Started at: {formatTimestamp(currentSession.started_at)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Session length: {(() => {
                        const start = new Date(currentSession.started_at).getTime();
                        const end = currentSession.ended_at ? new Date(currentSession.ended_at).getTime() : Date.now();
                        const diffMs = end - start;
                        const hours = Math.floor(diffMs / 3600000);
                        const minutes = Math.floor((diffMs % 3600000) / 60000);
                        const seconds = Math.floor((diffMs % 60000) / 1000);
                        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                      })()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Last update: {formatTimestamp(lastUpdatedIso)}
                    </Typography>
                    {currentSession.operator_name && (
                      <Typography variant="caption" color="text.secondary">
                        Operator: {currentSession.operator_name}
                      </Typography>
                    )}
                    
                    {/* Markers List */}
                    {sessionMarkers.length > 0 && (
                      <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid', borderColor: 'divider' }}>
                        <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ mb: 0.5, display: 'block' }}>
                          Markers:
                        </Typography>
                        <Stack spacing={0.5}>
                          {sessionMarkers.map((marker) => {
                            const markerTime = new Date(new Date(currentSession.started_at!).getTime() + marker.offset_seconds * 1000);
                            return (
                              <Box 
                                key={marker.id} 
                                sx={{ 
                                  display: 'flex', 
                                  alignItems: 'center', 
                                  justifyContent: 'space-between',
                                  gap: 0.5,
                                }}
                              >
                                <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
                                  #{marker.marker_number} - {formatTimestamp(markerTime.toISOString())}
                                  {marker.note && ` - ${marker.note}`}
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 0.5 }}>
                                  <Tooltip title="Edit marker note">
                                    <IconButton
                                      size="small"
                                      onClick={() => handleEditMarkerClick(marker)}
                                      sx={{ 
                                        padding: '2px',
                                        color: 'text.secondary',
                                        '&:hover': { 
                                          backgroundColor: 'action.hover',
                                          color: 'primary.main'
                                        }
                                      }}
                                    >
                                      <EditIcon sx={{ fontSize: 14 }} />
                                    </IconButton>
                                  </Tooltip>
                                  <Tooltip title="Delete marker">
                                    <IconButton
                                      size="small"
                                      onClick={() => handleDeleteMarker(marker.id)}
                                      sx={{ 
                                        padding: '2px',
                                        color: 'text.secondary',
                                        '&:hover': { 
                                          backgroundColor: 'action.hover',
                                          color: 'error.main'
                                        }
                                      }}
                                    >
                                      <DeleteIcon sx={{ fontSize: 14 }} />
                                    </IconButton>
                                  </Tooltip>
                                </Box>
                              </Box>
                            );
                          })}
                        </Stack>
                      </Box>
                    )}
                  </Stack>
                )}
              </Stack>
            )}
          </CardContent>
        </Card>

        {/* Right Card: Session Settings */}
        <Card sx={{ flex: 1, minWidth: 0 }}>
          <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Session Settings
            </Typography>
            
            <Stack spacing={2} sx={{ mt: 1.5 }}>
              {/* Session Management - Inline Editing */}
              {/* First Row: Add Marker button */}
              <Button
                variant="outlined"
                fullWidth
                onClick={handleAddMarkerClick}
                disabled={editState.mode !== 'none' || !currentSession.id}
                startIcon={<AddLocationIcon />}
                sx={{ 
                  textTransform: 'none',
                  height: '36px',
                }}
              >
                <Typography variant="h5" fontWeight={500}>
                  Add Marker
                </Typography>
              </Button>

              {/* Second Row: Rename button or input */}
              {editState.mode === 'renaming' ? (
                <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'stretch' }}>
                  <TextField
                    size="small"
                    fullWidth
                    autoFocus
                    value={editState.editValue}
                    onChange={(e) => setEditState(prev => ({ 
                      ...prev, 
                      editValue: e.target.value,
                      error: null
                    }))}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter session name..."
                    disabled={editState.loading}
                    error={!!editState.error}
                    helperText={editState.error}
                    inputProps={{ maxLength: 50 }}
                    sx={{ 
                      flex: 1,
                      '& .MuiInputBase-root': {
                        height: '32px',
                      }
                    }}
                  />
                  <Button
                    variant="outlined"
                    onClick={handleRenameConfirm}
                    disabled={editState.loading}
                    sx={{ 
                      minWidth: '32px',
                      width: '32px',
                      height: '32px',
                      p: 0,
                      borderColor: 'success.main',
                      color: 'success.main',
                      '&:hover': {
                        borderWidth: '2px',
                        borderColor: 'success.dark',
                      }
                    }}
                  >
                    {editState.loading ? (
                      <CircularProgress size={16} />
                    ) : (
                      <CheckIcon fontSize="small" />
                    )}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleEditCancel}
                    disabled={editState.loading}
                    sx={{ 
                      minWidth: '32px',
                      width: '32px',
                      height: '32px',
                      p: 0,
                      borderColor: 'error.main',
                      color: 'error.main',
                      '&:hover': {
                        borderWidth: '2px',
                        borderColor: 'error.dark',
                      }
                    }}
                  >
                    <CloseIcon fontSize="small" />
                  </Button>
                </Box>
              ) : (
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={handleRenameClick}
                  disabled={editState.mode === 'creating'}
                  sx={{ 
                    textTransform: 'none',
                    height: '36px',
                  }}
                >
                  <Typography variant="h5" fontWeight={500}>
                    Rename Current Session
                  </Typography>
                </Button>
              )}

              {/* Third Row: Start New button or input */}
              {editState.mode === 'creating' ? (
                <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'stretch' }}>
                  <TextField
                    size="small"
                    fullWidth
                    autoFocus
                    value={editState.editValue}
                    onChange={(e) => setEditState(prev => ({ 
                      ...prev, 
                      editValue: e.target.value,
                      error: null
                    }))}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter session name..."
                    disabled={editState.loading}
                    error={!!editState.error}
                    helperText={editState.error}
                    inputProps={{ maxLength: 50 }}
                    sx={{ 
                      flex: 1,
                      '& .MuiInputBase-root': {
                        height: '32px',
                      }
                    }}
                  />
                  <Button
                    variant="outlined"
                    onClick={handleNewSessionConfirm}
                    disabled={editState.loading}
                    sx={{ 
                      minWidth: '32px',
                      width: '32px',
                      height: '32px',
                      p: 0,
                      borderColor: 'success.main',
                      color: 'success.main',
                      '&:hover': {
                        borderWidth: '2px',
                        borderColor: 'success.dark',
                      }
                    }}
                  >
                    {editState.loading ? (
                      <CircularProgress size={16} />
                    ) : (
                      <CheckIcon fontSize="small" />
                    )}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleEditCancel}
                    disabled={editState.loading}
                    sx={{ 
                      minWidth: '32px',
                      width: '32px',
                      height: '32px',
                      p: 0,
                      borderColor: 'error.main',
                      color: 'error.main',
                      '&:hover': {
                        borderWidth: '2px',
                        borderColor: 'error.dark',
                      }
                    }}
                  >
                    <CloseIcon fontSize="small" />
                  </Button>
                </Box>
              ) : (
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={handleNewSessionClick}
                  disabled={editState.mode === 'renaming'}
                  sx={{ 
                    textTransform: 'none',
                    height: '36px',
                  }}
                >
                  <Typography variant="h5" fontWeight={500}>
                    Start New Session
                  </Typography>
                </Button>
              )}

              {/* Stop Recording Button */}
              {recordingEnabled && currentSession.id && (
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={async () => {
                    if (!stopConfirmPending) {
                      // First click - ask for confirmation
                      setStopConfirmPending(true);
                      // Auto-reset after 3 seconds
                      setTimeout(() => setStopConfirmPending(false), 3000);
                    } else {
                      // Second click - stop recording and end session
                      try {
                        const { stopSession } = await import('../api/sessions');
                        await stopSession(currentSession.id!);
                        onRecordingToggle();
                        setStopConfirmPending(false);
                        // Refresh session data
                        const response = await fetch(`http://localhost:8050/api/sessions/${currentSession.id}`);
                        const sessionData = await response.json();
                        setCurrentSession(prev => ({
                          ...prev,
                          ended_at: sessionData.ended_at
                        }));
                      } catch (error) {
                        console.error('Failed to stop session:', error);
                        setStopConfirmPending(false);
                      }
                    }
                  }}
                  disabled={editState.mode !== 'none'}
                  sx={{ 
                    textTransform: 'none',
                    height: '36px',
                    borderColor: stopConfirmPending ? '#8B0000' : undefined,
                    color: stopConfirmPending ? '#8B0000' : undefined,
                    '&:hover': {
                      borderColor: stopConfirmPending ? '#8B0000' : undefined,
                    }
                  }}
                >
                  <Typography variant="h5" fontWeight={500}>
                    {stopConfirmPending ? 'Click Again to Confirm' : 'Stop Recording'}
                  </Typography>
                </Button>
              )}
              
              {/* Recording Status (when stopped) */}
              {!recordingEnabled && (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <FiberManualRecordIcon 
                      color="default" 
                      sx={{ fontSize: 16 }} 
                    />
                    <Typography variant="h5" color="text.secondary" fontWeight={500}>
                      Recording Stopped
                    </Typography>
                  </Box>
                </Box>
              )}

              {/* Chart Time Range Slider */}
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 0.5 }}>
                  <Typography variant="h5" color="text.secondary" fontWeight={500}>
                    Chart Time Range:
                  </Typography>
                  <Typography variant="h5" color="text.secondary" fontWeight={500}>
                    {timeRangeOptions[chartTimeRangeIndex]} minutes
                  </Typography>
                </Box>
                <Box sx={{ px: 1, pt: 1.5, pb: 0.5 }}>
                  <Slider
                    value={chartTimeRangeIndex}
                    onChange={handleTimeRangeChange}
                    min={0}
                    max={timeRangeOptions.length - 1}
                    step={1}
                    marks={timeRangeOptions.map((minutes, index) => ({
                      value: index,
                      label: minutes.toString(),
                    }))}
                    valueLabelDisplay="off"
                    sx={{
                      height: 4,
                      '& .MuiSlider-thumb': {
                        width: 12,
                        height: 12,
                        '&:hover': {
                          boxShadow: 'none',
                        },
                        '&.Mui-active': {
                          boxShadow: 'none',
                        },
                        '&.Mui-focusVisible': {
                          boxShadow: 'none',
                        },
                      },
                      '& .MuiSlider-rail': {
                        height: 3,
                      },
                      '& .MuiSlider-track': {
                        height: 3,
                      },
                      '& .MuiSlider-markLabel': {
                        fontSize: '0.875rem',
                        fontWeight: 500,
                      },
                    }}
                  />
                </Box>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Box>

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

      {/* Marker Dialog */}
      <Dialog 
        open={markerDialogOpen} 
        onClose={handleMarkerCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{editingMarkerId ? 'Edit Marker' : 'Add Marker'}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {editingMarkerId 
              ? 'Update the marker position and note.' 
              : 'Place a marker at the specified time in this session.'}
          </Typography>
          
          {/* Time Input */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              Marker Time (from session start)
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
              <TextField
                size="small"
                label="Hours"
                type="number"
                value={Math.floor(markerOffsetSeconds / 3600)}
                onChange={(e) => {
                  const hours = Math.max(0, parseInt(e.target.value) || 0);
                  const minutes = Math.floor((markerOffsetSeconds % 3600) / 60);
                  const seconds = markerOffsetSeconds % 60;
                  setMarkerOffsetSeconds(hours * 3600 + minutes * 60 + seconds);
                }}
                disabled={markerLoading}
                inputProps={{ min: 0, max: 99 }}
                sx={{ width: '80px' }}
              />
              <TextField
                size="small"
                label="Minutes"
                type="number"
                value={Math.floor((markerOffsetSeconds % 3600) / 60)}
                onChange={(e) => {
                  const hours = Math.floor(markerOffsetSeconds / 3600);
                  const minutes = Math.max(0, Math.min(59, parseInt(e.target.value) || 0));
                  const seconds = markerOffsetSeconds % 60;
                  setMarkerOffsetSeconds(hours * 3600 + minutes * 60 + seconds);
                }}
                disabled={markerLoading}
                inputProps={{ min: 0, max: 59 }}
                sx={{ width: '80px' }}
              />
              <TextField
                size="small"
                label="Seconds"
                type="number"
                value={markerOffsetSeconds % 60}
                onChange={(e) => {
                  const hours = Math.floor(markerOffsetSeconds / 3600);
                  const minutes = Math.floor((markerOffsetSeconds % 3600) / 60);
                  const seconds = Math.max(0, Math.min(59, parseInt(e.target.value) || 0));
                  setMarkerOffsetSeconds(hours * 3600 + minutes * 60 + seconds);
                }}
                disabled={markerLoading}
                inputProps={{ min: 0, max: 59 }}
                sx={{ width: '80px' }}
              />
              {currentSession.started_at && (
                <Typography variant="caption" color="text.secondary" sx={{ pt: 1.5, flex: 1 }}>
                  {(() => {
                    const markerTime = new Date(new Date(currentSession.started_at).getTime() + markerOffsetSeconds * 1000);
                    return formatTimestamp(markerTime.toISOString());
                  })()}
                </Typography>
              )}
            </Box>
          </Box>

          {/* Note Input */}
          <TextField
            fullWidth
            label="Note (optional)"
            value={markerNote}
            onChange={(e) => setMarkerNote(e.target.value)}
            error={!!markerError}
            helperText={markerError}
            disabled={markerLoading}
            multiline
            rows={2}
            placeholder="Enter a note for this marker..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleMarkerCancel} disabled={markerLoading}>
            Cancel
          </Button>
          <Button 
            onClick={handleMarkerConfirm} 
            variant="contained" 
            disabled={markerLoading}
            startIcon={markerLoading ? <CircularProgress size={16} /> : null}
          >
            {markerLoading 
              ? (editingMarkerId ? 'Updating...' : 'Adding...') 
              : (editingMarkerId ? 'Update Marker' : 'Add Marker')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default MeasurementPanel;
