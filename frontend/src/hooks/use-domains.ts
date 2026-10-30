import { useQuery } from '@tanstack/react-query';
import {
  api,
  type JobDomainItem,
  type JobDomainJobsResponse,
} from '@/services/api';

export function useDomains() {
  return useQuery<JobDomainItem[]>({
    queryKey: ['job-domains'],
    queryFn: () => api.getDomains(),
    staleTime: 15000,
  });
}

export function useDomainJobs(query: string | null) {
  return useQuery<JobDomainJobsResponse | null>({
    queryKey: ['domain-jobs', query],
    queryFn: async () => {
      if (!query) return null;
      return api.getDomainJobs(query);
    },
    enabled: Boolean(query),
    staleTime: 30000,
  });
}

