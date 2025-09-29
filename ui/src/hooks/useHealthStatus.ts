import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  fetchHealthStatus,
  healthQueryKey,
  type AnalyticsProfileSummary,
  type HealthResponse,
  type ResponseTimeTelemetry,
  type CommandMetricsHistoryEntry,
} from '../api/health';

const DEFAULT_REFRESH_MS = 5000;

export const useHealthStatus = (refreshMs: number = DEFAULT_REFRESH_MS) => {
  const query = useQuery<HealthResponse>({
    queryKey: healthQueryKey,
    queryFn: ({ signal }) => fetchHealthStatus(signal),
    refetchInterval: refreshMs,
    staleTime: refreshMs,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const commandHistory = useMemo<CommandMetricsHistoryEntry[]>(() => {
    if (!query.data?.command_metrics?.history) return [];
    return query.data.command_metrics.history;
  }, [query.data?.command_metrics?.history]);

  const analyticsProfile = useMemo<AnalyticsProfileSummary | null>(() => {
    return query.data?.analytics_profile ?? null;
  }, [query.data?.analytics_profile]);

  const responseTimes = useMemo<ResponseTimeTelemetry | null>(() => {
    return query.data?.response_times ?? null;
  }, [query.data?.response_times]);

  return {
    ...query,
    commandHistory,
    analyticsProfile,
    responseTimes,
  };
};
