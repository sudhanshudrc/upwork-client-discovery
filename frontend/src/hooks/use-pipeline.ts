import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  api,
  type SingleJobPipelineRequest,
  type SingleJobPipelineResponse,
} from '@/services/api';

export function useRunSinglePipeline() {
  const queryClient = useQueryClient();

  return useMutation<SingleJobPipelineResponse, Error, SingleJobPipelineRequest>({
    mutationFn: (payload: SingleJobPipelineRequest) => api.runPipeline(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['job-details', data.job_uid] });
      queryClient.invalidateQueries({ queryKey: ['job-leads', data.job_uid] });
      queryClient.invalidateQueries({ queryKey: ['job-intelligence', data.job_uid] });
    },
  });
}

