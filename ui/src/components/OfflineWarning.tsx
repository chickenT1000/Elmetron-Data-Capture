import { Box, Button, Modal, Paper, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CloseIcon from '@mui/icons-material/Close';

export interface OfflineWarningProps {
  open: boolean;
  onClose?: () => void;
}

const AUTO_CLOSE_DELAY_MS = 120000; // Auto-close tab after 2 minutes

export const OfflineWarning: React.FC<OfflineWarningProps> = ({ open, onClose }) => {
  const [countdown, setCountdown] = useState(AUTO_CLOSE_DELAY_MS / 1000);

  useEffect(() => {
    if (!open) {
      setCountdown(AUTO_CLOSE_DELAY_MS / 1000);
      return;
    }

    // Start countdown
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          // Auto-close the tab
          window.close();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [open]);

  const handleCloseTab = () => {
    window.close();
  };

  const handleDismiss = () => {
    if (onClose) {
      onClose();
    }
  };

  return (
    <Modal
      open={open}
      onClose={handleDismiss}
      aria-labelledby="offline-warning-title"
      aria-describedby="offline-warning-description"
      disableEscapeKeyDown
    >
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: { xs: '90%', sm: 600 },
          maxWidth: '100%',
        }}
      >
        <Paper
          elevation={24}
          sx={{
            p: 4,
            borderRadius: 2,
            border: '3px solid',
            borderColor: 'warning.main',
          }}
        >
          {/* Icon and Title */}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <WarningAmberIcon
              sx={{
                fontSize: 48,
                color: 'warning.main',
                mr: 2,
              }}
            />
            <Typography
              id="offline-warning-title"
              variant="h5"
              component="h2"
              fontWeight="bold"
            >
              Launcher Offline
            </Typography>
          </Box>

          {/* Description */}
          <Typography
            id="offline-warning-description"
            variant="body1"
            sx={{ mb: 2 }}
          >
            The Elmetron launcher has been closed and backend services are no longer running.
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            <strong>Consequences:</strong>
          </Typography>

          <Box component="ul" sx={{ mb: 3, pl: 2 }}>
            <Typography component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ❌ No new measurements will be captured
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ❌ Real-time dashboard will not update
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ✅ Historical data viewing and exports still work
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ✅ All captured data is safely saved to the database
            </Typography>
          </Box>

          <Typography
            variant="body2"
            color="warning.main"
            fontWeight="bold"
            sx={{ mb: 3 }}
          >
            📌 This tab will automatically close in {countdown} seconds...
          </Typography>

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            <Button
              variant="outlined"
              onClick={handleDismiss}
              sx={{ minWidth: 120 }}
            >
              Keep Tab Open
            </Button>
            <Button
              variant="contained"
              color="error"
              startIcon={<CloseIcon />}
              onClick={handleCloseTab}
              sx={{ minWidth: 120 }}
            >
              Close Tab Now
            </Button>
          </Box>
        </Paper>
      </Box>
    </Modal>
  );
};
