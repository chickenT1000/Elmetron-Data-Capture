import { useQuery } from '@tanstack/react-query';
import { fetchHealthStatus, healthQueryKey, type HealthResponse } from '../api/health';

const DEFAULT_REFRESH_MS = 5000;

export const useHealthStatus = (refreshMs: number = DEFAULT_REFRESH_MS) =>
  useQuery<HealthResponse>({
    queryKey: healthQueryKey,
    queryFn: ({ signal }) => fetchHealthStatus(signal),
    refetchInterval: refreshMs,
    staleTime: refreshMs,
    refetchOnWindowFocus: false,
    retry: 1,
  });
