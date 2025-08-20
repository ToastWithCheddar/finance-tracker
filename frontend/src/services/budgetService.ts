import { apiClient } from './api';
import { BaseService } from './base/BaseService';
import type { ServiceResponse } from './base/BaseService';
import { BudgetPeriod } from '../types/budgets';
import type { 
  Budget, 
  BudgetFilters, 
  BudgetListResponse, 
  BudgetProgress, 
  BudgetSummary, 
  BudgetAlert, 
  BudgetUsage, 
  UpdateBudgetRequest,
  CreateBudgetRequest,
  BudgetCalendarResponse
} from '../types/budgets';

// Enhanced types from standardized service
export interface BudgetAnalytics {
  total_budgets: number;
  active_budgets: number;
  over_budget_count: number;
  total_budgeted_amount_cents: number;
  total_spent_amount_cents: number;
  average_utilization: number;
  trends: Array<{
    period: string;
    budgeted_cents: number;
    spent_cents: number;
    utilization: number;
  }>;
}

export interface BudgetComparison {
  current_period: {
    budgeted_cents: number;
    spent_cents: number;
    utilization: number;
  };
  previous_period: {
    budgeted_cents: number;
    spent_cents: number;
    utilization: number;
  };
  change: {
    budgeted_cents: number;
    spent_cents: number;
    utilization: number;
  };
}


class BudgetService extends BaseService {
  protected readonly baseEndpoint = '/budgets';

  // Legacy methods (maintain backward compatibility)
  async getBudgets(filters?: BudgetFilters): Promise<BudgetListResponse> {
    const params: Record<string, string | number | boolean> = {};
    
    if (filters?.category_id) params.category_id = filters.category_id;
    if (filters?.period) params.period = filters.period;
    if (filters?.is_active !== undefined) params.is_active = filters.is_active;
    if (filters?.over_budget !== undefined) params.over_budget = filters.over_budget;
    if (filters?.skip) params.skip = filters.skip;
    if (filters?.limit) params.limit = filters.limit;

    return apiClient.get<BudgetListResponse>('/budgets', params);
  }

  // ServiceResponse wrapper variant
  async getBudgetsWithWrapper(filters?: BudgetFilters): Promise<ServiceResponse<BudgetListResponse>> {
    try {
      const data = await this.getBudgets(filters);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: { 
          budgets: [], 
          summary: {
            total_budgets: 0,
            active_budgets: 0,
            total_budgeted_cents: 0,
            total_spent_cents: 0,
            total_remaining_cents: 0,
            over_budget_count: 0,
            alert_count: 0
          },
          alerts: []
        }
      } as ServiceResponse<BudgetListResponse>;
    }
  }

  async getBudget(budgetId: string): Promise<Budget> {
    return apiClient.get<Budget>(`/budgets/${budgetId}`);
  }

  async createBudget(budget: CreateBudgetRequest): Promise<Budget> {
    return apiClient.post<Budget>('/budgets', budget);
  }

  async updateBudget(budgetId: string, budget: UpdateBudgetRequest): Promise<Budget> {
    return apiClient.put<Budget>(`/budgets/${budgetId}`, budget);
  }

  async deleteBudget(budgetId: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/budgets/${budgetId}`);
  }

  async getBudgetProgress(budgetId: string): Promise<BudgetProgress> {
    return apiClient.get<BudgetProgress>(`/budgets/${budgetId}/progress`);
  }

  async getBudgetSummary(): Promise<BudgetSummary> {
    return apiClient.get<BudgetSummary>('/budgets/analytics/summary');
  }

  async getBudgetAlerts(): Promise<BudgetAlert[]> {
    return apiClient.get<BudgetAlert[]>('/budgets/analytics/alerts');
  }

  async getBudgetCalendar(budgetId: string, month: string): Promise<BudgetCalendarResponse> {
    const params = { month };
    return apiClient.get<BudgetCalendarResponse>(`/budgets/${budgetId}/calendar`, params);
  }

  // Helper methods
  formatCurrency(cents: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(cents) / 100);
  }

  formatPercentage(percentage: number): string {
    return `${percentage.toFixed(1)}%`;
  }

  getBudgetStatus(usage?: BudgetUsage): 'on-track' | 'warning' | 'over-budget' | 'unknown' {
    if (!usage) return 'unknown';
    
    if (usage.is_over_budget) return 'over-budget';
    if (usage.percentage_used >= 80) return 'warning';
    return 'on-track';
  }

  getBudgetStatusColor(status: string): string {
    switch (status) {
      case 'on-track': return 'text-green-600';
      case 'warning': return 'text-yellow-600';
      case 'over-budget': return 'text-red-600';
      default: return 'text-gray-600';
    }
  }

  getBudgetStatusBgColor(status: string): string {
    switch (status) {
      case 'on-track': return 'bg-green-100';
      case 'warning': return 'bg-yellow-100';
      case 'over-budget': return 'bg-red-100';
      default: return 'bg-gray-100';
    }
  }

  getPeriodDisplayName(period: BudgetPeriod): string {
    switch (period) {
      case BudgetPeriod.WEEKLY: return 'Weekly';
      case BudgetPeriod.MONTHLY: return 'Monthly';
      case BudgetPeriod.QUARTERLY: return 'Quarterly';
      case BudgetPeriod.YEARLY: return 'Yearly';
      default: return period;
    }
  }

  calculateDaysRemaining(usage?: BudgetUsage): string {
    if (!usage?.days_remaining) return 'N/A';
    
    if (usage.days_remaining === 0) return 'Last day';
    if (usage.days_remaining === 1) return '1 day left';
    return `${usage.days_remaining} days left`;
  }

  // Enhanced methods from standardized service
  async getBudgetAnalytics(period?: BudgetPeriod): Promise<BudgetAnalytics> {
    const params = period ? { period } : {};
    return apiClient.get<BudgetAnalytics>(`${this.baseEndpoint}/analytics`, params);
  }

  async getBudgetAnalyticsWithWrapper(period?: BudgetPeriod): Promise<ServiceResponse<BudgetAnalytics>> {
    try {
      const data = await this.getBudgetAnalytics(period);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: {
          total_budgets: 0,
          active_budgets: 0,
          over_budget_count: 0,
          total_budgeted_amount_cents: 0,
          total_spent_amount_cents: 0,
          average_utilization: 0,
          trends: []
        }
      } as ServiceResponse<BudgetAnalytics>;
    }
  }

  async getBudgetComparison(
    currentPeriodStart: string,
    currentPeriodEnd: string,
    previousPeriodStart: string,
    previousPeriodEnd: string
  ): Promise<BudgetComparison> {
    const params = {
      current_start: currentPeriodStart,
      current_end: currentPeriodEnd,
      previous_start: previousPeriodStart,
      previous_end: previousPeriodEnd
    };
    return apiClient.get<BudgetComparison>(`${this.baseEndpoint}/comparison`, params);
  }

  async getBudgetComparisonWithWrapper(
    currentPeriodStart: string,
    currentPeriodEnd: string,
    previousPeriodStart: string,
    previousPeriodEnd: string
  ): Promise<ServiceResponse<BudgetComparison>> {
    try {
      const data = await this.getBudgetComparison(
        currentPeriodStart, currentPeriodEnd, 
        previousPeriodStart, previousPeriodEnd
      );
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: {
          current_period: { budgeted_cents: 0, spent_cents: 0, utilization: 0 },
          previous_period: { budgeted_cents: 0, spent_cents: 0, utilization: 0 },
          change: { budgeted_cents: 0, spent_cents: 0, utilization: 0 }
        }
      } as ServiceResponse<BudgetComparison>;
    }
  }

  async getActiveBudgets(): Promise<Budget[]> {
    const response = await this.getBudgets({ is_active: true });
    return response.budgets;
  }

  async getActiveBudgetsWithWrapper(): Promise<ServiceResponse<Budget[]>> {
    try {
      const data = await this.getActiveBudgets();
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: []
      } as ServiceResponse<Budget[]>;
    }
  }

  async getOverBudgetItems(): Promise<Budget[]> {
    const response = await this.getBudgets({ over_budget: true });
    return response.budgets;
  }

  async getOverBudgetItemsWithWrapper(): Promise<ServiceResponse<Budget[]>> {
    try {
      const data = await this.getOverBudgetItems();
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: []
      } as ServiceResponse<Budget[]>;
    }
  }

  async getBudgetsByCategory(categoryId: string): Promise<Budget[]> {
    const response = await this.getBudgets({ category_id: categoryId });
    return response.budgets;
  }

  async getBudgetsByCategoryWithWrapper(categoryId: string): Promise<ServiceResponse<Budget[]>> {
    try {
      const data = await this.getBudgetsByCategory(categoryId);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: []
      } as ServiceResponse<Budget[]>;
    }
  }

  async getBudgetsByPeriod(period: BudgetPeriod): Promise<Budget[]> {
    const response = await this.getBudgets({ period });
    return response.budgets;
  }

  async getBudgetsByPeriodWithWrapper(period: BudgetPeriod): Promise<ServiceResponse<Budget[]>> {
    try {
      const data = await this.getBudgetsByPeriod(period);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      return {
        success: false,
        data: []
      } as ServiceResponse<Budget[]>;
    }
  }

  // Additional utility methods from standardized service
  calculateUtilization(budgetedAmount: number, spentAmount: number): number {
    if (budgetedAmount <= 0) return 0;
    return Math.round((spentAmount / budgetedAmount) * 100);
  }

  isOverThreshold(budgetedAmount: number, spentAmount: number, threshold: number = 0.8): boolean {
    const utilization = this.calculateUtilization(budgetedAmount, spentAmount);
    return utilization >= (threshold * 100);
  }

  isExceeded(budgetedAmount: number, spentAmount: number): boolean {
    return spentAmount > budgetedAmount;
  }

  getBudgetStatusDetailed(budgetedAmount: number, spentAmount: number, threshold: number = 0.8): 'good' | 'warning' | 'exceeded' {
    if (this.isExceeded(budgetedAmount, spentAmount)) {
      return 'exceeded';
    }
    
    if (this.isOverThreshold(budgetedAmount, spentAmount, threshold)) {
      return 'warning';
    }
    
    return 'good';
  }
}

export const budgetService = new BudgetService();
export { BudgetService };