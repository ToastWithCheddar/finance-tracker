import { BaseService } from './base/BaseService';

// Dashboard filter interface
export interface DashboardFilters {
  start_date?: string;
  end_date?: string;
  category_id?: string;
  account_id?: string;
  amount_min?: number;
  amount_max?: number;
}

// Category breakdown interface
export interface CategoryBreakdown {
  category_name: string;
  category_id: string;
  total_amount: number;
  transaction_count: number;
  percentage: number;
}

// Net worth trend data interface
export interface NetWorthTrendData {
  date: string;
  net_worth: number;
}

// Dashboard summary interface
export interface DashboardSummary {
  net_worth: number;
  total_liquid: number;
  total_debt: number;
  total_investment: number;
  financial_health_score: number;
  financial_health_grade: string;
  account_count: number;
  recent_transactions: number;
  recommendations: string[];
}

// Transaction histogram data interface
export interface TransactionHistogramBin {
  range_min: number;
  range_max: number;
  count: number;
  amount_total: number;
  range_label: string;
}

export interface TransactionHistogramData {
  bins: TransactionHistogramBin[];
  statistics: {
    total_transactions: number;
    total_amount: number;
    mean_amount: number;
    median_amount: number;
    min_amount: number;
    max_amount: number;
  };
  filters_applied: DashboardFilters;
}

export class DashboardService extends BaseService {
  protected baseEndpoint = '/dashboard';

  // Get dashboard data with filters
  async getDashboardData(filters?: DashboardFilters) {
    return this.get('', this.buildParams(filters || {}));
  }

  // Get category breakdown  
  async getCategoryBreakdown(filters?: DashboardFilters): Promise<CategoryBreakdown[]> {
    return this.get('category-breakdown', this.buildParams(filters || {}));
  }

  // Get net worth trend data
  async getNetWorthTrend(period: string = '90d'): Promise<NetWorthTrendData[]> {
    return this.get('net-worth-trend', { period });
  }

  // Get dashboard summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.get('summary');
  }

  getDateRangePresets() {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    const yearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    return {
      'Last 7 days': { startDate: weekAgo, endDate: today },
      'Last 30 days': { startDate: monthAgo, endDate: today },
      'Last year': { startDate: yearAgo, endDate: today },
    };
  }
}

export const dashboardService = new DashboardService();
export default dashboardService;