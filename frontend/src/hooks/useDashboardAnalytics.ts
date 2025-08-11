import { useQuery } from '@tanstack/react-query';

import { dashboardService } from '../services/dashboardService';

export const useDashboardAnalytics = () => {
  return useQuery({
    queryKey: ['dashboardAnalytics'],
    queryFn: () => dashboardService.getDashboardSummary({
      context: { operation: 'fetchDashboardAnalytics' }
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
};