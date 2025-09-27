import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked';
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd';

const metricCards = [
  { label: 'pH', value: '6.98', helper: 'Stable' },
  { label: 'Temperature', value: '22.3 °C', helper: 'Compensated' },
  { label: 'Conductivity', value: '1.23 mS/cm', helper: 'Trending up' },
  { label: 'Dissolved O₂', value: '8.4 mg/L', helper: 'Within tolerance' },
];

export default function DashboardPage() {
  return (
    <Stack spacing={3}>
      <Card>
        <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2 }}>
          <Box>
            <Typography variant="h5" fontWeight={600} gutterBottom>
              Live Monitoring & Recording
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Control CX-505 recording sessions, add bookmarks, and follow real-time measurements.
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button startIcon={<RadioButtonCheckedIcon />} color="error" variant="contained">
              Stop Recording
            </Button>
            <Button variant="outlined" startIcon={<BookmarkAddIcon />}>
              Add Bookmark
            </Button>
          </Stack>
        </CardContent>
      </Card>
      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        }}
      >
        {metricCards.map((metric) => (
          <Card key={metric.label}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                {metric.label}
              </Typography>
              <Typography variant="h4" fontWeight={600}>
                {metric.value}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Updated just now • {metric.helper}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
      <Card sx={{ minHeight: 320 }}>
        <CardContent>
          <Typography variant="h6" mb={2} display="flex" alignItems="center" gap={1}>
            <ShowChartIcon color="primary" /> Live Parameter Trends
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
            Time-series chart placeholder (pH, temperature, conductivity, O₂)
          </Box>
        </CardContent>
      </Card>
      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
        }}
      >
        <Card sx={{ minHeight: 220 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Active Session Timeline
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Visualise bookmarks, calibration events, and annotations aligned to recording time.
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ minHeight: 220 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Alerts & Diagnostics
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Watchdog warnings, threshold alerts, and scheduled command updates surface here.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Stack>
  );
}
