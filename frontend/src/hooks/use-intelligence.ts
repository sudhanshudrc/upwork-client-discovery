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
    { status: string; intelligence: ConfirmedIntelligence },
    Error,
    {
      job_id: string;
      job_uid: string;
      confirmed_client_name: string;
      confirmed_company_name: string;
      target_role?: string;
      is_agency?: boolean;
    }
  >({
    mutationFn: ({ job_id, confirmed_client_name, confirmed_company_name, target_role, is_agency }) =>
      api.confirmIntelligence({
        job_id,
        confirmed_client_name,
        confirmed_company_name,
        target_role,
        is_agency,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['job-details', variables.job_uid] });
      queryClient.invalidateQueries({ queryKey: ['job-intelligence', variables.job_uid] });
    },
  });
}

