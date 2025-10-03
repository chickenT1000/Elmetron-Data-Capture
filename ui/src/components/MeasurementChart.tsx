import React from 'react';
import { Box, Typography, Paper, CircularProgress } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { TooltipProps } from 'recharts';
import type { MeasurementDataPoint } from '../hooks/useRecentMeasurements';

interface MeasurementChartProps {
  title: string;
  data: MeasurementDataPoint[];
  dataKey: 'ph' | 'redox' | 'conductivity' | 'temperature';
  color: string;
  unit: string;
  loading?: boolean;
  yAxisDomain?: [number, number] | ['auto', 'auto'];
  decimalPlaces?: number;
}

const CustomTooltip: React.FC<
  TooltipProps<number, string> & {
    unit: string;
    decimalPlaces: number;
  }
> = ({ active, payload, unit, decimalPlaces }) => {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;
  const value = payload[0].value;

  // Format timestamp
  const date = new Date(data.timestamp);
  const timeStr = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <Paper
      sx={{
        padding: 1.5,
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        border: '1px solid #ccc',
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
        {timeStr}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {value !== null && value !== undefined
          ? `${value.toFixed(decimalPlaces)} ${unit}`
          : 'N/A'}
      </Typography>
    </Paper>
  );
};

export const MeasurementChart: React.FC<MeasurementChartProps> = ({
  title,
  data,
  dataKey,
  color,
  unit,
  loading = false,
  yAxisDomain = ['auto', 'auto'],
  decimalPlaces = 2,
}) => {
  // Filter out null/undefined values for this specific metric
  const filteredData = data.filter(
    (d) => d[dataKey] !== null && d[dataKey] !== undefined
  );

  // Format time for X-axis
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Paper
      elevation={2}
      sx={{
        padding: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      {loading ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: 200,
          }}
        >
          <CircularProgress size={40} />
        </Box>
      ) : filteredData.length === 0 ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: 200,
            color: 'text.secondary',
          }}
        >
          <Typography variant="body2">No data available</Typography>
        </Box>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart
            data={filteredData}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              stroke="#666"
              style={{ fontSize: '12px' }}
              minTickGap={50}
            />
            <YAxis
              domain={yAxisDomain}
              stroke="#666"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => value.toFixed(decimalPlaces)}
            />
            <Tooltip
              content={<CustomTooltip unit={unit} decimalPlaces={decimalPlaces} />}
            />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mt: 1, textAlign: 'center' }}
      >
        {filteredData.length > 0
          ? `${filteredData.length} data points`
          : 'Waiting for measurements...'}
      </Typography>
    </Paper>
  );
};
