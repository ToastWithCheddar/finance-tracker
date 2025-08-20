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

export function useMoneyFlow(startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['money-flow', startDate, endDate],
    queryFn: () => dashboardService.getMoneyFlow({ start_date: startDate, end_date: endDate }),
    enabled: !!startDate && !!endDate,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
  });
}

export function useSpendingHeatmap(startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['spending-heatmap', startDate, endDate],
    queryFn: () => dashboardService.getSpendingHeatmap({ start_date: startDate, end_date: endDate }),
    enabled: !!startDate && !!endDate,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
  });
}

export function useNetWorthTrend(period: string = '90d') {
  return useQuery({
    queryKey: ['net-worth-trend', period],
    queryFn: () => dashboardService.getNetWorthTrend(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useCashFlowWaterfall(startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['cash-flow-waterfall', startDate, endDate],
    queryFn: () => dashboardService.getCashFlowWaterfall({ start_date: startDate, end_date: endDate }),
    enabled: !!startDate && !!endDate,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
  });
}