import { Box, Button, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import ScienceIcon from '@mui/icons-material/Science';
import HistoryIcon from '@mui/icons-material/History';

export default function CalibrationsPage() {
  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Typography variant="h5" fontWeight={600} gutterBottom>
            Calibration Center
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Launch calibration routines, review protocol details, and audit historical runs.
          </Typography>
        </CardContent>
      </Card>
      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
        }}
      >
        {[1, 2, 3].map((idx) => (
          <Card key={idx}>
            <CardContent>
              <Stack spacing={1.5}>
                <Typography variant="subtitle2" color="text.secondary">
                  Calibration Command
                </Typography>
                <Typography variant="h6">Buffer {idx * 3 + 4} Routine</Typography>
                <Chip label="Last run: 2025-09-26 10:21" size="small" color="success" />
                <Typography variant="body2" color="text.secondary">
                  Executes CX-505 calibration request with automatic retries and audit tracking.
                </Typography>
                <Button startIcon={<ScienceIcon />}>Trigger Calibration</Button>
                <Button startIcon={<HistoryIcon />} variant="outlined">
                  View History
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Stack>
  );
}
