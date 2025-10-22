import { useQuery } from '@tanstack/react-query';
import { buildApiUrl } from '../config';

export interface LiveStatusResponse {
  live_capture_active: boolean;
  device_connected: boolean;
  mode: 'live' | 'archive';
  current_session_id: number | null;
  last_update: string | null;
  instrument?: {
    model: string;
    serial: string;
    description: string;
  } | null;
}

const fetchLiveStatus = async (signal?: AbortSignal): Promise<LiveStatusResponse> => {
  const response = await fetch(buildApiUrl('/api/live/status'), { signal });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch live status: ${response.statusText}`);
  }
  
  return response.json();
};

export const liveStatusQueryKey = ['liveStatus'];

const DEFAULT_REFRESH_MS = 3000; // Poll every 3 seconds

export const useLiveStatus = (refreshMs: number = DEFAULT_REFRESH_MS) => {
  return useQuery<LiveStatusResponse>({
    queryKey: liveStatusQueryKey,
    queryFn: ({ signal }) => fetchLiveStatus(signal),
    refetchInterval: refreshMs,
    staleTime: refreshMs,
    refetchOnWindowFocus: true,
    retry: 2,
  });
};
