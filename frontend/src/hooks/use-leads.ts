import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type DecisionMakerDiscoveryResponse } from '@/services/api';

export function useDiscoverLeads() {
  const queryClient = useQueryClient();

  return useMutation<DecisionMakerDiscoveryResponse, Error, string>({
    mutationFn: (jobUid: string) => api.discoverLeads(jobUid),
    onSuccess: (data, jobUid) => {
      queryClient.setQueryData(['job-leads', jobUid], data);
      queryClient.invalidateQueries({ queryKey: ['job-details', jobUid] });
    },
  });
}

export function useJobLeads(jobUid: string | null) {
  return useQuery<DecisionMakerDiscoveryResponse>({
    queryKey: ['job-leads', jobUid],
    queryFn: () => {
      if (!jobUid) throw new Error('No job UID provided');
      return api.discoverLeads(jobUid);
    },
    enabled: false, // Triggered on demand or when cached
  });
}

