import { Box, Button, Modal, Paper, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CloseIcon from '@mui/icons-material/Close';

export interface OfflineWarningProps {
  open: boolean;
  onClose?: () => void;
}

export const OfflineWarning: React.FC<OfflineWarningProps> = ({ open, onClose }) => {
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
              ❌ Historical data viewing is unavailable (backend offline)
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ❌ Exports are unavailable (backend offline)
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ✅ All captured data is safely saved to the database
            </Typography>
          </Box>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 3 }}
          >
            💡 <strong>You can safely close this browser tab now.</strong> Nothing will work until you restart the launcher.
          </Typography>

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              onClick={handleDismiss}
              sx={{ minWidth: 120 }}
            >
              Dismiss
            </Button>
          </Box>
        </Paper>
      </Box>
    </Modal>
  );
};
