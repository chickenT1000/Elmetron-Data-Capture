import React, { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
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
import { useChartAutoScaling } from '../hooks/useChartAutoScaling';

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
  autoScalingEnabled?: boolean;
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
  autoScalingEnabled = true,
}) => {
  // Get auto-scaled domain and ticks from hook
  const { domain: autoScaleDomain, ticks: autoScaleTicks, preset } = useChartAutoScaling({
    data,
    dataKey,
    enabled: autoScalingEnabled,
    bufferPercent: 0.10,
  });

  // Use auto-scaling if enabled, otherwise use manual domain
  const effectiveDomain = autoScalingEnabled ? autoScaleDomain : yAxisDomain;
  const effectiveTicks = autoScalingEnabled ? autoScaleTicks : undefined;

  // Debug logging (only once on mount or when data changes significantly)
  React.useEffect(() => {
    if (dataKey === 'ph' && data.length > 0) {
      console.log('[MeasurementChart pH] Auto-scaling:', {
        enabled: autoScalingEnabled,
        autoScaleDomain: JSON.stringify(autoScaleDomain),
        autoScaleTicks: JSON.stringify(autoScaleTicks),
        effectiveDomain: JSON.stringify(effectiveDomain),
        effectiveTicks: JSON.stringify(effectiveTicks),
        preset: preset.label,
        dataPoints: data.length,
        filteredDataPoints: data.filter(d => d[dataKey] !== null && d[dataKey] !== undefined).length,
        sampleData: data.slice(0, 3).map(d => ({ ph: d.ph, time: d.timestamp })),
      });
    }
  }, [data.length, dataKey]); // Only log when data length changes
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
  // LOGIC: If temperature data exists in a gap, the device was connected but this channel
  // wasn't being measured (mode switching) → BREAK the line
  // If no temperature data in gap, device was offline → use threshold to decide
  const dataWithGapBreaks = React.useMemo(() => {
    if (filteredData.length === 0) return filteredData;
    
    const GAP_THRESHOLD_MINUTES = gapThresholdSeconds / 60; // Convert seconds to minutes
    const result = [];
    
    // Build array of temperature data points with their actual timestamps
    // We need the original timestamps, not minutesAgo (which changes every render)
    const temperatureData = chartData
      .filter(point => point.temperature !== null && point.temperature !== undefined)
      .map(point => ({
        timestamp: new Date(point.timestamp).getTime(),
        minutesAgo: point.minutesAgo,
      }));
    
    for (let i = 0; i < filteredData.length; i++) {
      result.push(filteredData[i]);
      
      // Check if there's a gap to the next point
      if (i < filteredData.length - 1) {
        const currentPoint = filteredData[i];
        const nextPoint = filteredData[i + 1];
        
        const currentTimestamp = new Date(currentPoint.timestamp).getTime();
        const nextTimestamp = new Date(nextPoint.timestamp).getTime();
        const gapMs = nextTimestamp - currentTimestamp;
        const gapMinutes = gapMs / 60000;
        
        // Debug logging for gaps
        if (gapMinutes > GAP_THRESHOLD_MINUTES && dataKey === 'ph') {
          console.log(`[${dataKey}] Gap detected:`, {
            gapSeconds: gapMs / 1000,
            thresholdSeconds: gapThresholdSeconds,
            currentTime: new Date(currentTimestamp).toISOString(),
            nextTime: new Date(nextTimestamp).toISOString(),
          });
        }
        
        // Check if temperature (reference) has data points in this gap
        const temperaturePointsInGap = temperatureData.filter(tempPoint => {
          return tempPoint.timestamp > currentTimestamp && tempPoint.timestamp < nextTimestamp;
        });
        
        const temperatureHasDataInGap = temperaturePointsInGap.length > 0;
        
        if (dataKey === 'ph' && gapMinutes > GAP_THRESHOLD_MINUTES) {
          console.log(`[${dataKey}] Temperature data in gap:`, {
            hasData: temperatureHasDataInGap,
            count: temperaturePointsInGap.length,
            gapMinutes: gapMinutes.toFixed(2),
          });
        }
        
        // Decision logic:
        // 1. If temperature HAS data in gap → device connected, channel intentionally not measured → BREAK
        // 2. If temperature has NO data AND gap > threshold → device offline for too long → BREAK
        // 3. If temperature has NO data AND gap <= threshold → timing variation, keep connected
        
        if (temperatureHasDataInGap) {
          // Case 1: Temperature present but this channel missing → mode switching
          if (dataKey === 'ph') {
            console.log(`[${dataKey}] Breaking line: temperature present, channel missing (mode switch)`);
          }
          result.push({
            ...currentPoint,
            [dataKey]: null, // This breaks the line
            minutesAgo: (currentPoint.minutesAgo + nextPoint.minutesAgo) / 2,
          });
        } else if (gapMinutes > GAP_THRESHOLD_MINUTES) {
          // Case 2: No temperature data and gap too large → device offline
          if (dataKey === 'ph') {
            console.log(`[${dataKey}] Breaking line: no temperature, gap too large (device offline)`);
          }
          result.push({
            ...currentPoint,
            [dataKey]: null,
            minutesAgo: (currentPoint.minutesAgo + nextPoint.minutesAgo) / 2,
          });
        }
        // Case 3: No temperature and gap within threshold → keep connected (timing variation)
      }
    }
    
    return result;
  }, [filteredData, dataKey, gapThresholdSeconds, chartData]);

  // Merge actual data with dummy data for full hover coverage
  // Strategy: Start with all actual data, then add dummy points only in gaps
  const combinedData = React.useMemo(() => {
    // Start with all actual measurement data
    const result = [...dataWithGapBreaks];
    
    // Add dummy points only where there's no nearby actual data
    // This ensures hover works across the entire time range
    for (const dummyPoint of dummyDataForHover) {
      const hasNearbyData = dataWithGapBreaks.some(
        actualPoint => Math.abs(actualPoint.minutesAgo - dummyPoint.minutesAgo) < 0.3
      );
      
      if (!hasNearbyData) {
        // Add dummy point with all measurement fields undefined
        // This allows hover to work but won't render any line
        result.push({
          ...dummyPoint,
          timestamp: new Date(Date.now() + dummyPoint.minutesAgo * 60000).toISOString(),
          // Don't set measurement fields - leave them undefined
        });
      }
    }
    
    // Sort by time
    return result.sort((a, b) => a.minutesAgo - b.minutesAgo);
  }, [dataWithGapBreaks, dummyDataForHover]);

  // Debug: log the data with gap breaks
  if (dataKey === 'ph' && dataWithGapBreaks.length > 0) {
    console.log(`[${dataKey}] dataWithGapBreaks count:`, dataWithGapBreaks.length);
    console.log(`[${dataKey}] Null points in data:`, dataWithGapBreaks.filter(d => d[dataKey] === null).length);
    console.log(`[${dataKey}] Sample data:`, dataWithGapBreaks.slice(0, 5).map(d => ({ 
      time: d.minutesAgo, 
      value: d[dataKey] 
    })));
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

  // Check if data is actively incoming (has recent data within last 5 seconds)
  // IMPORTANT: Check actual timestamp, not minutesAgo (which is recalculated every render)
  const hasRecentData = React.useMemo(() => {
    if (filteredData.length === 0) return false;
    const mostRecentPoint = filteredData[filteredData.length - 1];
    
    // Calculate actual time difference using timestamps
    const dataTimestamp = new Date(mostRecentPoint.timestamp).getTime();
    const currentTime = Date.now();
    const ageMilliseconds = currentTime - dataTimestamp;
    
    // Data is "incoming" if most recent point is less than 5 seconds old
    // This makes the indicator very responsive to mode changes
    return ageMilliseconds < 5000; // 5 seconds in milliseconds
  }, [filteredData]);

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, ml: 6 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FiberManualRecordIcon 
            color={hasRecentData ? 'success' : 'default'} 
            sx={{ fontSize: 12 }} 
          />
          <Typography variant="h6">
            {title}
          </Typography>
        </Box>
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
            style={{ backgroundColor: '#ffffff' }}
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
            <CartesianGrid strokeDasharray="3 3" stroke="#999" />
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
              domain={effectiveDomain}
              ticks={effectiveTicks}
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
    </Box>
  );
};
