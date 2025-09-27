import { useQuery, type UseQueryOptions, type UseQueryResult } from '@tanstack/react-query';

import { fetchSessionEvaluation, type SessionEvaluationResponse } from '../api/sessions';

export const sessionEvaluationQueryKey = (sessionId: number, anchor: string) =>
  ['session-evaluation', sessionId, anchor] as const;

export const sessionEvaluationQueryOptions = (
  sessionId: number,
  anchor: string,
): UseQueryOptions<SessionEvaluationResponse> => ({
  queryKey: sessionEvaluationQueryKey(sessionId, anchor),
  queryFn: () => fetchSessionEvaluation(sessionId, { anchor }),
  staleTime: 30_000,
});

export function useSessionEvaluation(
  sessionId: number,
  anchor: string,
): UseQueryResult<SessionEvaluationResponse> {
  return useQuery(sessionEvaluationQueryOptions(sessionId, anchor));
}
