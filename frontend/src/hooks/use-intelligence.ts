import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type IntelligenceMiningResponse, type ConfirmedIntelligence } from '@/services/api';

export function useIntelligence(jobUid: string | null) {
  return useQuery<IntelligenceMiningResponse | null>({
    queryKey: ['job-intelligence', jobUid],
    queryFn: async () => {
      if (!jobUid) return null;
      try {
        return await api.getIntelligence(jobUid);
      } catch {
        return null;
      }
    },
    enabled: Boolean(jobUid),
    staleTime: 60000,
    retry: false,
  });
}

export function useConfirmIntelligence() {
  const queryClient = useQueryClient();

  return useMutation<
    ConfirmedIntelligence,
    Error,
    {
      job_id?: string;
      job_uid?: string;
      confirmed_client_name: string;
      confirmed_company_name?: string;
      target_role?: string;
      is_agency?: boolean;
    }
  >({
    mutationFn: (payload) => api.confirmIntelligence(payload),
    onSuccess: (_data, variables) => {
      if (variables.job_uid) {
        queryClient.invalidateQueries({ queryKey: ['job-details', variables.job_uid] });
        queryClient.invalidateQueries({ queryKey: ['job-intelligence', variables.job_uid] });
      }
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-clients'] });
      queryClient.invalidateQueries({ queryKey: ['harvested-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['job-domains'] });
    },
  });
}

