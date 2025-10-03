import React from 'react';
import { Box, Typography, Paper, Alert } from '@mui/material';
import { MeasurementChart } from './MeasurementChart';
import { useRecentMeasurements } from '../hooks/useRecentMeasurements';

interface RollingChartsPanelProps {
  windowMinutes?: number;
}

export const RollingChartsPanel: React.FC<RollingChartsPanelProps> = ({
  windowMinutes = 10,
}) => {
  const { data, loading, error, sessionId } = useRecentMeasurements(
    windowMinutes,
    2000, // Poll every 2 seconds
    true
  );

  return (
    <Box sx={{ mb: 3 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" component="h2">
            Rolling Measurement Trends
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Last {windowMinutes} minutes
            {sessionId && ` - Session #${sessionId}`}
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load measurement data: {error.message}
          </Alert>
        )}

        {!loading && !error && data.length === 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            No measurement data available. Start a capture session to see live trends.
          </Alert>
        )}

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
          <Box>
            <MeasurementChart
              title="pH"
              data={data}
              dataKey="ph"
              color="#2196f3"
              unit="pH"
              loading={loading}
              yAxisDomain={[0, 14]}
              decimalPlaces={2}
            />
          </Box>

          <Box>
            <MeasurementChart
              title="Redox (ORP)"
              data={data}
              dataKey="redox"
              color="#ff9800"
              unit="mV"
              loading={loading}
              yAxisDomain={[-2000, 2000]}
              decimalPlaces={1}
            />
          </Box>

          <Box>
            <MeasurementChart
              title="Conductivity"
              data={data}
              dataKey="conductivity"
              color="#4caf50"
              unit="µS/cm"
              loading={loading}
              yAxisDomain={['auto', 'auto']}
              decimalPlaces={1}
            />
          </Box>

          <Box>
            <MeasurementChart
              title="Temperature"
              data={data}
              dataKey="temperature"
              color="#f44336"
              unit="°C"
              loading={loading}
              yAxisDomain={['auto', 'auto']}
              decimalPlaces={1}
            />
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};
