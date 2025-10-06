import React, { useState, useEffect } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Slider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
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
  });
  
  // Session editing state
  const [editState, setEditState] = useState<SessionEditState>({
    mode: 'none',
    editValue: '',
    loading: false,
    error: null,
  });

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
          // Fetch session details to get the name
          const sessionResponse = await fetch(`http://localhost:8050/api/sessions/${data.current_session_id}`);
          const sessionData = await sessionResponse.json();
          
          setCurrentSession({
            id: sessionData.id,
            session_number: sessionData.id, // Using ID as session number for now
            name: sessionData.note,
            display_name: sessionData.note || `Session ${sessionData.id}`,
            started_at: sessionData.started_at,
          });
        } else {
          // No active session
          setCurrentSession({
            id: null,
            session_number: null,
            name: null,
            display_name: 'No active session',
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
                        const now = Date.now();
                        const diffMs = now - start;
                        const hours = Math.floor(diffMs / 3600000);
                        const minutes = Math.floor((diffMs % 3600000) / 60000);
                        const seconds = Math.floor((diffMs % 60000) / 1000);
                        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                      })()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Last update: {formatTimestamp(lastUpdatedIso)}
                    </Typography>
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
              {/* First Row: Rename button or input */}
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

              {/* Second Row: Start New button or input */}
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

              {/* Recording Toggle */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <FiberManualRecordIcon 
                    color={recordingEnabled ? 'success' : 'default'} 
                    sx={{ fontSize: 16 }} 
                  />
                  <Typography variant="h5" color="text.secondary" fontWeight={500}>
                    Recording
                  </Typography>
                </Box>
                <Switch 
                  size="medium" 
                  checked={recordingEnabled ?? false}
                  onChange={onRecordingToggle}
                  disabled={!isLiveMode}
                />
              </Box>

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
    </>
  );
};

export default MeasurementPanel;
