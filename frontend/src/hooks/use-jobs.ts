import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  api,
  type JobSearchResponse,
  type JobDetailRecord,
  type JobExpandResponse,
} from '@/services/api';

export function useJobDetails(jobUid: string | null) {
  return useQuery<JobDetailRecord | null>({
    queryKey: ['job-details', jobUid],
    queryFn: async () => {
      if (!jobUid) return null;
      try {
        return await api.getJob(jobUid);
      } catch (err: unknown) {
        // If 404, job is in Stage 1 (feed extracted) and not yet expanded into PostgreSQL
        return null;
      }
    },
    enabled: Boolean(jobUid),
    staleTime: 60000,
    retry: false,
  });
}

export function useJobSearch() {
  const queryClient = useQueryClient();

  return useMutation<
    JobSearchResponse,
    Error,
    { query: string; limit?: number; forceLive?: boolean }
  >({
    mutationFn: ({ query, limit = 5, forceLive = false }) =>
      api.searchJobs(query, limit, forceLive),
    onSuccess: (data) => {
      queryClient.setQueryData(['latest-job-search'], data);
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['job-domains'] });
    },
  });
}

export function useExpandJob() {
  const queryClient = useQueryClient();

  return useMutation<
    JobExpandResponse,
    Error,
    { jobUid: string; jobUrl?: string; forceLive?: boolean }
  >({
    mutationFn: ({ jobUid, jobUrl, forceLive = false }) =>
      api.expandJob(jobUid, jobUrl, forceLive),
    onSuccess: (_data, variables) => {
      // Invalidate and refetch job details and mined intelligence
      queryClient.invalidateQueries({ queryKey: ['job-details', variables.jobUid] });
      queryClient.invalidateQueries({ queryKey: ['job-intelligence', variables.jobUid] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-clients'] });
      queryClient.invalidateQueries({ queryKey: ['all-harvested-jobs'] });
    },
  });
}

