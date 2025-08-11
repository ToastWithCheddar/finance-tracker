/**
 * Standardized Budget Service using BaseService patterns
 */
import { BaseService } from '../base/BaseService';
import type { ServiceResponse, BaseFilters } from '../base/BaseService';
import type { 
  Budget, 
  BudgetListResponse, 
  BudgetProgress, 
  BudgetSummary, 
  BudgetAlert, 
  UpdateBudgetRequest,
  CreateBudgetRequest,
  BudgetPeriod
} from '../../types/budgets';

// Budget-specific filters
export interface BudgetFilters extends BaseFilters {
  category_id?: string;
  period?: BudgetPeriod;
  is_active?: boolean;
  over_budget?: boolean;
  alert_threshold_min?: number;
  alert_threshold_max?: number;
  start_date?: string;
  end_date?: string;
}

// Budget analytics types
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

export class StandardizedBudgetService extends BaseService {
  protected readonly baseEndpoint = '/budgets';
  
  /**
   * Get budgets with filters and pagination
   */
  async getBudgets(filters?: BudgetFilters): Promise<ServiceResponse<BudgetListResponse>> {
    const params = this.buildParams(filters || {});
    return this.getWithWrapper<BudgetListResponse>(this.baseEndpoint, params);
  }
  
  /**
   * Get a single budget by ID
   */
  async getBudget(id: string): Promise<ServiceResponse<Budget>> {
    return this.getWithWrapper<Budget>(this.buildEndpoint(id));
  }
  
  /**
   * Create a new budget
   */
  async createBudget(budget: CreateBudgetRequest): Promise<ServiceResponse<Budget>> {
    return this.postWithWrapper<Budget>(this.baseEndpoint, budget);
  }
  
  /**
   * Update an existing budget
   */
  async updateBudget(id: string, budget: UpdateBudgetRequest): Promise<ServiceResponse<Budget>> {
    return this.putWithWrapper<Budget>(this.buildEndpoint(id), budget);
  }
  
  /**
   * Delete a budget
   */
  async deleteBudget(id: string): Promise<ServiceResponse<{ message: string }>> {
    return this.deleteWithWrapper<{ message: string }>(this.buildEndpoint(id));
  }
  
  /**
   * Get budget progress/usage details
   */
  async getBudgetProgress(id: string): Promise<ServiceResponse<BudgetProgress>> {
    return this.getWithWrapper<BudgetProgress>(this.buildEndpoint(`${id}/progress`));
  }
  
  /**
   * Get budget summary statistics
   */
  async getBudgetSummary(filters?: BudgetFilters): Promise<ServiceResponse<BudgetSummary>> {
    const params = this.buildParams(filters || {});
    return this.getWithWrapper<BudgetSummary>(this.buildEndpoint('summary'), params);
  }
  
  /**
   * Get budget alerts
   */
  async getBudgetAlerts(): Promise<ServiceResponse<BudgetAlert[]>> {
    return this.getWithWrapper<BudgetAlert[]>(this.buildEndpoint('alerts'));
  }
  
  /**
   * Get budget analytics
   */
  async getBudgetAnalytics(period?: BudgetPeriod): Promise<ServiceResponse<BudgetAnalytics>> {
    const params = period ? { period } : {};
    return this.getWithWrapper<BudgetAnalytics>(this.buildEndpoint('analytics'), params);
  }
  
  /**
   * Get budget comparison between periods
   */
  async getBudgetComparison(
    currentPeriodStart: string,
    currentPeriodEnd: string,
    previousPeriodStart: string,
    previousPeriodEnd: string
  ): Promise<ServiceResponse<BudgetComparison>> {
    const params = {
      current_start: currentPeriodStart,
      current_end: currentPeriodEnd,
      previous_start: previousPeriodStart,
      previous_end: previousPeriodEnd
    };
    return this.getWithWrapper<BudgetComparison>(this.buildEndpoint('comparison'), params);
  }
  
  /**
   * Get active budgets only
   */
  async getActiveBudgets(): Promise<ServiceResponse<Budget[]>> {
    const response = await this.getBudgets({ is_active: true });
    
    if (response.success && response.data) {
      return {
        ...response,
        data: response.data.budgets
      };
    }
    
    return response as ServiceResponse<Budget[]>;
  }
  
  /**
   * Get over-budget items
   */
  async getOverBudgetItems(): Promise<ServiceResponse<Budget[]>> {
    const response = await this.getBudgets({ over_budget: true });
    
    if (response.success && response.data) {
      return {
        ...response,
        data: response.data.budgets
      };
    }
    
    return response as ServiceResponse<Budget[]>;
  }
  
  /**
   * Get budgets by category
   */
  async getBudgetsByCategory(categoryId: string): Promise<ServiceResponse<Budget[]>> {
    const response = await this.getBudgets({ category_id: categoryId });
    
    if (response.success && response.data) {
      return {
        ...response,
        data: response.data.budgets
      };
    }
    
    return response as ServiceResponse<Budget[]>;
  }
  
  /**
   * Get budgets by period
   */
  async getBudgetsByPeriod(period: BudgetPeriod): Promise<ServiceResponse<Budget[]>> {
    const response = await this.getBudgets({ period });
    
    if (response.success && response.data) {
      return {
        ...response,
        data: response.data.budgets
      };
    }
    
    return response as ServiceResponse<Budget[]>;
  }
  
  /**
   * Get period display name for UI
   */
  getPeriodDisplayName(period: BudgetPeriod): string {
    switch (period) {
      case 'weekly': return 'Weekly';
      case 'monthly': return 'Monthly';
      case 'quarterly': return 'Quarterly';
      case 'yearly': return 'Yearly';
      default: return 'Unknown';
    }
  }
  
  /**
   * Calculate budget utilization percentage
   */
  calculateUtilization(budgetedAmount: number, spentAmount: number): number {
    if (budgetedAmount <= 0) return 0;
    return Math.round((spentAmount / budgetedAmount) * 100);
  }
  
  /**
   * Check if budget is over threshold
   */
  isOverThreshold(budgetedAmount: number, spentAmount: number, threshold: number = 0.8): boolean {
    const utilization = this.calculateUtilization(budgetedAmount, spentAmount);
    return utilization >= (threshold * 100);
  }
  
  /**
   * Check if budget is exceeded
   */
  isExceeded(budgetedAmount: number, spentAmount: number): boolean {
    return spentAmount > budgetedAmount;
  }
  
  /**
   * Get budget status based on utilization
   */
  getBudgetStatus(budgetedAmount: number, spentAmount: number, threshold: number = 0.8): 'good' | 'warning' | 'exceeded' {
    if (this.isExceeded(budgetedAmount, spentAmount)) {
      return 'exceeded';
    }
    
    if (this.isOverThreshold(budgetedAmount, spentAmount, threshold)) {
      return 'warning';
    }
    
    return 'good';
  }
}

// Create and export singleton instance
export const budgetService = new StandardizedBudgetService();