import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { fetchRecentSessions, type SessionSummary } from '../api/sessions';

export const recentSessionsQueryKey = (limit: number) => ['session-list', limit] as const;

export function useRecentSessions(limit: number = 10): UseQueryResult<SessionSummary[]> {
  return useQuery({
    queryKey: recentSessionsQueryKey(limit),
    queryFn: () => fetchRecentSessions({ limit }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
