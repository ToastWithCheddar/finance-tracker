import { apiClient } from './api';

export interface DashboardAnalytics {
  period: {
    start_date: string;
    end_date: string;
  };
  summary: {
    total_income: number;
    total_expenses: number;
    net_amount: number;
    transaction_count: number;
  };
  category_breakdown: CategoryBreakdown[];
  recent_transactions: RecentTransaction[];
}

export interface CategoryBreakdown {
  category_name: string;
  total_amount: number;
  transaction_count: number;
  percentage: number;
}

export interface RecentTransaction {
  id: string;
  amount: number;
  category: string;
  description: string;
  transaction_date: string;
  transaction_type: string;
}

export interface SpendingTrend {
  period: string;
  income: number;
  expenses: number;
  net: number;
}

export interface DashboardFilters {
  start_date?: string;
  end_date?: string;
  period?: 'weekly' | 'monthly';
}

class DashboardService {
  async getDashboardAnalytics(filters?: DashboardFilters): Promise<DashboardAnalytics> {
    const params: Record<string, string> = {};
    
    if (filters?.start_date) params.start_date = filters.start_date;
    if (filters?.end_date) params.end_date = filters.end_date;

    return apiClient.get<DashboardAnalytics>('/transactions/analytics/dashboard', params);
  }

  async getSpendingTrends(period: 'weekly' | 'monthly' = 'monthly'): Promise<SpendingTrend[]> {
    return apiClient.get<SpendingTrend[]>('/transactions/analytics/trends', { period });
  }

  // Helper method to get predefined date ranges
  getDateRangePresets(): Record<string, { start_date: string; end_date: string }> {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    
    // This week
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    const thisWeekStart = startOfWeek.toISOString().split('T')[0];
    
    // This month
    const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
    
    // Last month
    const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0).toISOString().split('T')[0];
    
    // This year
    const thisYearStart = new Date(now.getFullYear(), 0, 1).toISOString().split('T')[0];
    
    // Last 30 days
    const last30Days = new Date(now);
    last30Days.setDate(now.getDate() - 30);
    const last30DaysStart = last30Days.toISOString().split('T')[0];

    return {
      today: { start_date: today, end_date: today },
      thisWeek: { start_date: thisWeekStart, end_date: today },
      thisMonth: { start_date: thisMonthStart, end_date: today },
      lastMonth: { start_date: lastMonthStart, end_date: lastMonthEnd },
      thisYear: { start_date: thisYearStart, end_date: today },
      last30Days: { start_date: last30DaysStart, end_date: today },
    };
  }
}

export const dashboardService = new DashboardService();