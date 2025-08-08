import { apiClient } from './api';
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
  CreateBudgetRequest
} from '../types/budgets';


class BudgetService {
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
}

export const budgetService = new BudgetService();