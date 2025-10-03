import React, { useState, useEffect } from 'react';
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
  // Force re-render every second to update the time positions
  const [, setTick] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1);
    }, 1000); // Update every second
    
    return () => clearInterval(interval);
  }, []);
  
  // Use actual current time as reference point for "now" (position 0)
  // This makes the chart scroll in real-time as new data arrives
  const now = Date.now();
  
  // Transform data to use relative time from NOW
  // Recent data will be near 0, older data will be more negative
  const chartData = data.map((d) => {
    const dataTimestamp = new Date(d.timestamp).getTime();
    const minutesAgo = (dataTimestamp - now) / 60000; // Will be negative for past data
    
    return {
      ...d,
      minutesAgo: minutesAgo,
    };
  });

  // Filter out null/undefined values for this specific metric
  // Also filter to only show data within the 10-minute window and sort chronologically
  const filteredData = chartData
    .filter((d) => d[dataKey] !== null && d[dataKey] !== undefined)
    .filter((d) => d.minutesAgo >= -10 && d.minutesAgo <= 0)
    .sort((a, b) => a.minutesAgo - b.minutesAgo);

  // Debug logging to see what's happening
  if (dataKey === 'temperature' && filteredData.length > 0) {
    console.log(`[${title}] Now: ${new Date(now).toLocaleTimeString()}`);
    console.log(`[${title}] Newest data:`, filteredData[filteredData.length - 1]);
    console.log(`[${title}] minutesAgo range: ${filteredData[0]?.minutesAgo.toFixed(2)} to ${filteredData[filteredData.length - 1]?.minutesAgo.toFixed(2)}`);
  }

  // Format time for X-axis (show minutes ago)
  const formatTime = (minutesAgo: number) => {
    if (minutesAgo === 0) return 'now';
    const absMinutes = Math.abs(Math.round(minutesAgo));
    return `-${absMinutes}m`;
  };

  // Fixed domain constants to prevent Recharts from auto-adjusting
  const xDomain: [number, number] = [-10, 0];
  const xTicks = [-10, -8, -6, -4, -2, 0];

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
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart
            data={filteredData}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis
              dataKey="minutesAgo"
              type="number"
              domain={xDomain}
              tickFormatter={formatTime}
              ticks={xTicks}
              stroke="#666"
              style={{ fontSize: '12px' }}
              allowDataOverflow={true}
              scale="linear"
            />
            <YAxis
              domain={yAxisDomain}
              stroke="#666"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => value.toFixed(decimalPlaces)}
              allowDataOverflow={true}
              scale="linear"
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
              connectNulls={false}
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
