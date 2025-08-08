import { useQuery } from '@tanstack/react-query';
import { dashboardService, type DashboardFilters } from '../services/dashboardService';

export function useDashboardAnalytics(filters?: DashboardFilters) {
  return useQuery({
    queryKey: ['dashboard-analytics', filters],
    queryFn: () => dashboardService.getDashboardAnalytics(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (gcTime is the correct property in v5)
  });
}

export function useSpendingTrends(period: 'weekly' | 'monthly' = 'monthly') {
  return useQuery({
    queryKey: ['spending-trends', period],
    queryFn: () => dashboardService.getSpendingTrends(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (gcTime is the correct property in v5)
  });
}

export function useDashboardDateRanges() {
  return dashboardService.getDateRangePresets();
}