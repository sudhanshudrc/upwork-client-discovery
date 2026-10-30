import { useQuery } from '@tanstack/react-query';
import {
  api,
  type DashboardStatsResponse,
  type DashboardClientItem,
  type HarvestedJobItem,
} from '@/services/api';

export function useDashboardStats() {
  return useQuery<DashboardStatsResponse>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
    staleTime: 15000,
    refetchInterval: 30000,
  });
}

export function useDashboardClients() {
  return useQuery<DashboardClientItem[]>({
    queryKey: ['dashboard-clients'],
    queryFn: () => api.getDashboardClients(),
    staleTime: 30000,
  });
}

export function useAllHarvestedJobs() {
  return useQuery<HarvestedJobItem[]>({
    queryKey: ['all-harvested-jobs'],
    queryFn: () => api.getAllHarvestedJobs(),
    staleTime: 30000,
  });
}

