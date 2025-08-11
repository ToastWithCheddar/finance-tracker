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
  transactionCount: number;
  date: string;
}

export interface DashboardFilters {
  period?: 'week' | 'month' | 'quarter' | 'year';
  startDate?: string;
  endDate?: string;
  categoryId?: string;
  accountId?: string;
}

export class DashboardService extends BaseService {
  protected baseEndpoint = '/analytics';

  async getDashboardSummary(options?: { context?: ErrorContext }): Promise<DashboardAnalytics> {
    const response = await this.get<{ success: boolean; data: DashboardAnalytics }>(
      this.buildEndpoint('/dashboard'),
      undefined,
      { context: options?.context, useCache: true, cacheTtl: 5 * 60 * 1000 } // Cache for 5 mins
    );

    if (response && response.success && response.data) {
      return response.data;
    }
    throw new Error('Failed to fetch dashboard summary or data is invalid.');
  }
}

export const dashboardService = new DashboardService();