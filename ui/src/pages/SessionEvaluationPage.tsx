import { Box, Button, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import AlignHorizontalCenterIcon from '@mui/icons-material/AlignHorizontalCenter';
import CropIcon from '@mui/icons-material/Crop';
import DownloadIcon from '@mui/icons-material/Download';

export default function SessionEvaluationPage() {
  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Typography variant="h5" fontWeight={600} gutterBottom>
            Session Evaluation & Overlays
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Compare recordings, align overlays, crop segments, and export consolidated insights.
          </Typography>
        </CardContent>
      </Card>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '280px 1fr' },
          gap: 3,
        }}
      >
        <Card sx={{ minHeight: 320 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Session Selector
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose one or more sessions to overlay. Tag filters and previews appear here.
            </Typography>
            <Stack spacing={1} mt={3}>
              {['Session 24 - Buffer 7', 'Session 25 - O₂ Probe', 'Session 26 - Conductivity'].map((label) => (
                <Chip key={label} label={label} variant="outlined" />
              ))}
            </Stack>
          </CardContent>
        </Card>
        <Card sx={{ minHeight: 320 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Overlay Workspace
            </Typography>
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
              }}
            >
              Overlay plot with alignment controls placeholder
            </Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} mt={2}>
              <Button startIcon={<AlignHorizontalCenterIcon />} variant="outlined">
                Align on Calibration Marker
              </Button>
              <Button startIcon={<CropIcon />} variant="outlined">
                Trim to Selection
              </Button>
              <Button startIcon={<DownloadIcon />}>Export Overlay</Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
          gap: 3,
        }}
      >
        <Card sx={{ minHeight: 220 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Metrics Summary
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Compare min/max/average, stability index, temperature compensation for each overlay.
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ minHeight: 220 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Comparison Notes
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Capture analyst conclusions; saved with overlay exports and revision history.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Stack>
  );
}
