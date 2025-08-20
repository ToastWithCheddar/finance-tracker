import { BaseService } from './base/BaseService';
import type { ErrorContext } from '../types/errors';

export interface DashboardAnalytics {
  totalBalance: number;
  totalTransactions: number;
  recentTransactions: Array<{
    id: string;
    description: string;
    amountCents: number;
    date: string;
  }>;
  spendingByCategory: Record<string, number>;
  // Additional properties expected by RealtimeDashboard
  summary?: {
    total_income: number;
    total_expenses: number;
    net_amount: number;
    transaction_count: number;
  };
  category_breakdown?: CategoryBreakdown[];
  period?: string;
}

export interface CategoryBreakdown {
  category: string;
  amountCents: number;
  transactionCount: number;
  percentage: number;
}

export interface SpendingTrend {
  period: string;
  amountCents: number;
  income: number;
  expenses: number;
  transactionCount: number;
  date: string;
}

export interface DashboardFilters {
  period?: 'week' | 'month' | 'quarter' | 'year';
  start_date?: string;
  end_date?: string;
  category_id?: string;
  account_id?: string;
}

export interface MoneyFlowNode {
  id: string;
  label?: string;
  color?: string;
}

export interface MoneyFlowLink {
  source: string;
  target: string;
  value: number;
}

export interface MoneyFlowData {
  nodes: MoneyFlowNode[];
  links: MoneyFlowLink[];
  metadata: {
    total_income: number;
    total_expenses: number;
    net_savings: number;
    date_range: {
      start_date: string;
      end_date: string;
    };
    income_sources_count: number;
    expense_categories_count: number;
  };
}

export interface SpendingHeatmapData {
  day: string;
  value: number;
}

export interface NetWorthDataPoint {
  date: string;
  net_worth_cents: number;
  net_worth: number;
}

export interface CashFlowData {
  start_balance_cents: number;
  total_income_cents: number;
  total_expenses_cents: number;
  end_balance_cents: number;
  start_balance: number;
  total_income: number;
  total_expenses: number;
  end_balance: number;
}

export class DashboardService extends BaseService {
  protected baseEndpoint = '/analytics';

  async getDashboardSummary(options?: { context?: ErrorContext }): Promise<DashboardAnalytics> {
    const response = await this.get<{ success: boolean; data: DashboardAnalytics }>(
      '/dashboard',
      undefined,
      { context: options?.context, useCache: true, cacheTtl: 5 * 60 * 1000 } // Cache for 5 mins
    );

    if (response && response.success && response.data) {
      return response.data;
    }
    throw new Error('Failed to fetch dashboard summary or data is invalid.');
  }

  async getDashboardAnalytics(filters?: DashboardFilters, options?: { context?: ErrorContext }): Promise<DashboardAnalytics> {
    // For now, delegate to getDashboardSummary until proper filtered analytics are implemented
    return this.getDashboardSummary(options);
  }

  async getSpendingTrends(period: 'weekly' | 'monthly' = 'monthly', options?: { context?: ErrorContext }): Promise<SpendingTrend[]> {
    // Placeholder implementation - would need actual API endpoint
    return [];
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

  async getMoneyFlow(params: { start_date: string; end_date: string }, options?: { context?: ErrorContext }): Promise<MoneyFlowData> {
    const response = await this.get<{ success: boolean; data: MoneyFlowData; message?: string }>(
      '/money-flow',
      { start_date: params.start_date, end_date: params.end_date },
      { context: options?.context, useCache: true, cacheTtl: 10 * 60 * 1000 } // Cache for 10 mins
    );

    if (response && response.success && response.data) {
      return response.data;
    }
    throw new Error(response?.message || 'Failed to fetch money flow data or data is invalid.');
  }

  async getSpendingHeatmap(params: { start_date: string; end_date: string }, options?: { context?: ErrorContext }): Promise<SpendingHeatmapData[]> {
    const response = await this.get<{ success: boolean; data: SpendingHeatmapData[] }>(
      '/spending-heatmap',
      { start_date: params.start_date, end_date: params.end_date },
      { context: options?.context, useCache: true, cacheTtl: 10 * 60 * 1000 } // Cache for 10 mins
    );

    if (response && response.success && response.data) {
      return response.data;
    }
    throw new Error('Failed to fetch spending heatmap data or data is invalid.');
  }

  async getNetWorthTrend(period: string = '90d', options?: { context?: ErrorContext }): Promise<NetWorthDataPoint[]> {
    const response = await this.get<{ success: boolean; data: NetWorthDataPoint[]; message?: string }>(
      '/net-worth-trend',
      { period },
      { context: options?.context, useCache: true, cacheTtl: 5 * 60 * 1000 } // Cache for 5 mins
    );

    if (response && response.success && response.data) {
      return response.data;
    }
    throw new Error(response?.message || 'Failed to fetch net worth trend data or data is invalid.');
  }

  async getCashFlowWaterfall(params: { start_date: string; end_date: string }, options?: { context?: ErrorContext }): Promise<CashFlowData> {
    const response = await this.get<{ success: boolean; data: CashFlowData }>(
      '/cash-flow-waterfall',
      { start_date: params.start_date, end_date: params.end_date },
      { context: options?.context, useCache: true, cacheTtl: 10 * 60 * 1000 } // Cache for 10 mins
    );

    if (response && response.success && response.data) {
      return response.data;
    }
    throw new Error('Failed to fetch cash flow waterfall data or data is invalid.');
  }
}

export const dashboardService = new DashboardService();
export default dashboardService;