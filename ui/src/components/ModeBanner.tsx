import { Alert, AlertTitle, Box, Chip, Collapse } from '@mui/material';
import ArchiveIcon from '@mui/icons-material/Archive';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { useLiveStatus } from '../hooks/useLiveStatus';

export function ModeBanner() {
  const { data: liveStatus, isLoading, isError } = useLiveStatus();

  // Don't show banner while loading or if there's an error
  if (isLoading || isError || !liveStatus) {
    return null;
  }

  const isArchiveMode = liveStatus.mode === 'archive';
  const isLiveMode = liveStatus.mode === 'live';

  return (
    <Box sx={{ mb: 2 }}>
      {/* Archive Mode Banner */}
      <Collapse in={isArchiveMode}>
        <Alert
          severity="info"
          icon={<ArchiveIcon />}
          sx={{
            backgroundColor: 'info.light',
            '& .MuiAlert-icon': {
              color: 'info.main',
            },
          }}
        >
          <AlertTitle sx={{ fontWeight: 600 }}>Archive Mode</AlertTitle>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <Box>
              The CX-505 device is not connected. You can browse historical sessions and view past measurements,
              but live data capture is unavailable.
            </Box>
            <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                label="Device Offline"
                size="small"
                color="default"
                variant="outlined"
              />
              <Chip
                label="Read-Only Mode"
                size="small"
                color="info"
                variant="outlined"
              />
            </Box>
          </Box>
        </Alert>
      </Collapse>

      {/* Live Mode Banner */}
      <Collapse in={isLiveMode}>
        <Alert
          severity="success"
          icon={<FiberManualRecordIcon />}
          sx={{
            backgroundColor: 'success.light',
            '& .MuiAlert-icon': {
              color: 'success.main',
            },
          }}
        >
          <AlertTitle sx={{ fontWeight: 600 }}>Live Mode</AlertTitle>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <Box>
              The CX-505 device is connected and ready. You can start new capture sessions and view live measurements.
            </Box>
            <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                label="Device Connected"
                size="small"
                color="success"
                variant="outlined"
              />
              {liveStatus.current_session_id && (
                <Chip
                  label={`Session #${liveStatus.current_session_id}`}
                  size="small"
                  color="primary"
                  variant="filled"
                />
              )}
            </Box>
          </Box>
        </Alert>
      </Collapse>
    </Box>
  );
}
