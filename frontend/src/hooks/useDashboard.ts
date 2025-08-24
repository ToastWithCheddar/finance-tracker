import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '../services/dashboardService';
import type { NetWorthTrendData, DashboardSummary } from '../services/dashboardService';

export function useDashboardDateRanges() {
  return dashboardService.getDateRangePresets();
}

export function useNetWorthTrend(period: string = '90d') {
  return useQuery({
    queryKey: ['net-worth-trend', period],
    queryFn: () => dashboardService.getNetWorthTrend(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardService.getDashboardSummary(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}