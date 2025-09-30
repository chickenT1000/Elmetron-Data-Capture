import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';

export interface ConnectionStatus {
  isOnline: boolean;
  lastChecked: Date | null;
  consecutiveFailures: number;
}

const CHECK_INTERVAL_MS = 5000; // Check every 5 seconds
const MAX_FAILURES_BEFORE_OFFLINE = 2; // Consider offline after 2 consecutive failures

/**
 * Hook to monitor connection to the backend API.
 * Periodically pings the health endpoint and tracks online/offline status.
 */
export const useConnectionMonitor = () => {
  const [status, setStatus] = useState<ConnectionStatus>({
    isOnline: true,
    lastChecked: null,
    consecutiveFailures: 0,
  });

  useEffect(() => {
    let isMounted = true;
    let timeoutId: ReturnType<typeof setTimeout>;

    const checkConnection = async () => {
      try {
        const controller = new AbortController();
        const timeoutMs = 3000; // 3 second timeout per request
        
        const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          signal: controller.signal,
          // Disable cache to ensure fresh checks
          cache: 'no-store',
        });

        clearTimeout(timeoutHandle);

        if (isMounted) {
          if (response.ok) {
            // Connection successful
            setStatus({
              isOnline: true,
              lastChecked: new Date(),
              consecutiveFailures: 0,
            });
          } else {
            // Bad response
            setStatus((prev) => {
              const failures = prev.consecutiveFailures + 1;
              return {
                isOnline: failures < MAX_FAILURES_BEFORE_OFFLINE,
                lastChecked: new Date(),
                consecutiveFailures: failures,
              };
            });
          }
        }
      } catch (error) {
        // Connection failed (network error, timeout, etc.)
        if (isMounted) {
          setStatus((prev) => {
            const failures = prev.consecutiveFailures + 1;
            return {
              isOnline: failures < MAX_FAILURES_BEFORE_OFFLINE,
              lastChecked: new Date(),
              consecutiveFailures: failures,
            };
          });
        }
      }

      // Schedule next check
      if (isMounted) {
        timeoutId = setTimeout(checkConnection, CHECK_INTERVAL_MS);
      }
    };

    // Start monitoring
    checkConnection();

    return () => {
      isMounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, []);

  return status;
};
