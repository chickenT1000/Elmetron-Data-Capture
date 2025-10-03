import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, CircularProgress } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { MeasurementDataPoint } from '../hooks/useRecentMeasurements';

interface MeasurementChartProps {
  title: string;
  data: MeasurementDataPoint[]; // All measurement data (all channels)
  dataKey: 'ph' | 'redox' | 'conductivity' | 'temperature';
  color: string;
  unit: string;
  loading?: boolean;
  yAxisDomain?: [number, number] | ['auto', 'auto'];
  decimalPlaces?: number;
  sharedHoverPosition?: number | null;
  onHoverChange?: (position: number | null) => void;
  gapThresholdSeconds?: number;
}

export const MeasurementChart: React.FC<MeasurementChartProps> = ({
  title,
  data,
  dataKey,
  color,
  unit,
  loading = false,
  yAxisDomain = ['auto', 'auto'],
  decimalPlaces = 2,
  sharedHoverPosition = null,
  onHoverChange,
  gapThresholdSeconds = 15,
}) => {
  // Force re-render every second to update the time positions
  const [, setTick] = useState(0);
  
  // Track hovered data point
  const [hoveredPoint, setHoveredPoint] = useState<any>(null);
  
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

  // Create dummy data points spanning the entire time range for hover detection
  // This ensures hover works even where there's no actual measurement data
  const dummyDataForHover = React.useMemo(() => {
    const points = [];
    for (let i = -10; i <= 0; i += 0.5) { // Every 30 seconds
      points.push({
        minutesAgo: i,
        dummyValue: 0, // Will be invisible
      });
    }
    return points;
  }, []);

  // Insert explicit null values in measurement data where gaps are too large
  // SMART GAP DETECTION: Use temperature as reference since it always streams in parallel
  // Only break the line if temperature has no data (device disconnected)
  // If temperature has data in the gap, keep lines connected (just channel timing variation)
  const dataWithGapBreaks = React.useMemo(() => {
    if (filteredData.length === 0) return filteredData;
    
    const GAP_THRESHOLD_MINUTES = gapThresholdSeconds / 60; // Convert seconds to minutes
    const result = [];
    
    // Build a set of timestamps where temperature (reference channel) has data
    // Temperature always streams, so if it has data, device was connected
    const temperatureTimestamps = new Set();
    chartData.forEach(point => {
      if (point.temperature !== null && point.temperature !== undefined) {
        temperatureTimestamps.add(point.minutesAgo);
      }
    });
    
    for (let i = 0; i < filteredData.length; i++) {
      result.push(filteredData[i]);
      
      // Check if there's a large gap to the next point
      if (i < filteredData.length - 1) {
        const currentTime = filteredData[i].minutesAgo;
        const nextTime = filteredData[i + 1].minutesAgo;
        const gap = Math.abs(nextTime - currentTime);
        
        // Debug logging
        if (gap > GAP_THRESHOLD_MINUTES && dataKey === 'ph') {
          console.log(`[${dataKey}] Large gap detected:`, {
            gap: gap * 60,
            gapSeconds: gap * 60,
            threshold: gapThresholdSeconds,
            currentTime,
            nextTime,
            temperatureTimestampsCount: temperatureTimestamps.size
          });
        }
        
        // CORRECT LOGIC:
        // - If temperature HAS data in gap → channel not measured intentionally → BREAK line
        // - If temperature has NO data in gap → device offline → CONNECT if gap < threshold
        if (gap > GAP_THRESHOLD_MINUTES) {
          // Check if temperature (reference) has data in the gap
          const temperatureHasDataInGap = Array.from(temperatureTimestamps).some(t => {
            const timestamp = t as number;
            return timestamp > currentTime && timestamp < nextTime;
          });
          
          if (dataKey === 'ph') {
            console.log(`[${dataKey}] Temperature has data in gap:`, temperatureHasDataInGap);
          }
          
          // If temperature HAS data, this channel wasn't being measured → BREAK the line
          if (temperatureHasDataInGap) {
            if (dataKey === 'ph') {
              console.log(`[${dataKey}] Temperature present but channel missing → Breaking line (intentional gap)`);
            }
            result.push({
              ...filteredData[i],
              [dataKey]: null, // This breaks the line
              minutesAgo: (currentTime + nextTime) / 2, // Place in middle of gap
            });
          }
          // If temperature has NO data, device was offline → keep connected (timing variation)
          else {
            if (dataKey === 'ph') {
              console.log(`[${dataKey}] No temperature data → Keeping connected (device offline, not intentional gap)`);
            }
          }
        }
      }
    }
    
    return result;
  }, [filteredData, dataKey, gapThresholdSeconds, chartData]);

  // Use dataWithGapBreaks directly for rendering
  // Hover will work where there's data, which is sufficient
  const combinedData = dataWithGapBreaks;

  // Format time for X-axis (show minutes ago)
  const formatTime = (minutesAgo: number) => {
    if (minutesAgo === 0) return 'now';
    const absMinutes = Math.abs(Math.round(minutesAgo));
    return `-${absMinutes}m`;
  };

  // Fixed domain constants to prevent Recharts from auto-adjusting
  const xDomain: [number, number] = [-10, 0];
  const xTicks = [-10, -8, -6, -4, -2, 0];

  // Find data point closest to shared hover position
  const hoverPoint = React.useMemo(() => {
    if (sharedHoverPosition === null || filteredData.length === 0) {
      return null;
    }
    
    // Find the closest data point to the hover position
    let closest = filteredData[0];
    let minDistance = Math.abs(filteredData[0].minutesAgo - sharedHoverPosition);
    
    for (const point of filteredData) {
      const distance = Math.abs(point.minutesAgo - sharedHoverPosition);
      if (distance < minDistance) {
        minDistance = distance;
        closest = point;
      }
    }
    
    // Only return if reasonably close (within 0.5 minutes)
    if (minDistance < 0.5) {
      return closest;
    }
    return null;
  }, [sharedHoverPosition, filteredData]);

  // Format hover value display
  const hoverDisplay = hoverPoint ? (
    <>
      <strong>{hoverPoint[dataKey]?.toFixed(decimalPlaces)} {unit}</strong>
      {' @ '}
      {new Date(hoverPoint.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })}
    </>
  ) : null;

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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, ml: 6 }}>
        <Typography variant="h6">
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {hoverDisplay}
        </Typography>
      </Box>

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
            data={combinedData}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            onMouseMove={(e: any) => {
              // Use activeLabel (x-axis value) for shared hover position
              if (e && e.activeLabel !== undefined) {
                const minutesAgo = e.activeLabel;
                console.log(`[${title}] Hover at x position:`, minutesAgo);
                
                // Find the closest data point for local hover display
                if (e.activePayload && e.activePayload.length > 0) {
                  setHoveredPoint(e.activePayload[0].payload);
                }
                
                // Update shared hover position for all charts
                if (onHoverChange) {
                  onHoverChange(minutesAgo);
                }
              }
            }}
            onMouseLeave={() => {
              setHoveredPoint(null);
              // Clear shared hover position
              if (onHoverChange) {
                onHoverChange(null);
              }
            }}
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
            {/* Show vertical guideline at shared hover position */}
            {sharedHoverPosition !== null && (
              <ReferenceLine
                x={sharedHoverPosition}
                stroke="#ccc"
                strokeWidth={1}
                strokeDasharray="3 3"
                isFront={true}
                label=""
              />
            )}
            {/* Measurement data line */}
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
