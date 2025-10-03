import { useState, useEffect } from 'react';
import { buildApiUrl } from '../config';

export interface MeasurementDataPoint {
  timestamp: string;
  timestampMs: number;
  ph?: number | null;
  redox?: number | null;
  conductivity?: number | null;
  temperature?: number | null;
}

interface UseRecentMeasurementsResult {
  data: MeasurementDataPoint[];
  loading: boolean;
  error: Error | null;
  sessionId: number | null;
}

export function useRecentMeasurements(
  windowMinutes: number = 10,
  pollingMs: number = 2000,
  enabled: boolean = true
): UseRecentMeasurementsResult {
  const [data, setData] = useState<MeasurementDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        const response = await fetch(buildApiUrl(`/api/measurements/recent?minutes=${windowMinutes}`));
        
        if (!response.ok) {
          throw new Error(`Failed to fetch measurements: ${response.statusText}`);
        }

        const result = await response.json();

        // Check if we have data
        if (!result.measurements || result.measurements.length === 0) {
          setData([]);
          setSessionId(result.session_id || null);
          setLoading(false);
          return;
        }

        // Transform measurements to add timestampMs for charting
        const measurements: MeasurementDataPoint[] = result.measurements.map((m: any) => ({
          timestamp: m.timestamp,
          timestampMs: new Date(m.timestamp).getTime(),
          ph: m.ph !== undefined && m.ph !== null ? Number(m.ph) : null,
          redox: m.redox !== undefined && m.redox !== null ? Number(m.redox) : null,
          conductivity:
            m.conductivity !== undefined && m.conductivity !== null
              ? Number(m.conductivity)
              : null,
          temperature:
            m.temperature !== undefined && m.temperature !== null
              ? Number(m.temperature)
              : null,
        }));

        setData(measurements);
        setSessionId(result.session_id);
        setLoading(false);
        setError(null);
      } catch (err) {
        console.error('Error fetching recent measurements:', err);
        setError(err as Error);
        setLoading(false);
      }
    };

    // Initial fetch
    fetchData();

    // Set up polling
    const interval = setInterval(fetchData, pollingMs);

    return () => clearInterval(interval);
  }, [windowMinutes, pollingMs, enabled]);

  return { data, loading, error, sessionId };
}
