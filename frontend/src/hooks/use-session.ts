import { useQuery } from '@tanstack/react-query';
import { api, type SessionStatusResponse } from '@/services/api';

export function useSessionStatus(userIdentifier?: string) {
  return useQuery<SessionStatusResponse>({
    queryKey: ['session-status', userIdentifier],
    queryFn: () => api.getSessionStatus(userIdentifier),
    staleTime: 30000,
    retry: 1,
  });
}
