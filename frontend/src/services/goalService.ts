import { apiClient } from './api';
import { GoalStatus, GoalType, GoalPriority } from '../types/goals';
import { BaseService } from './base/BaseService';
import type {
  Goal,
  GoalCreate,
  GoalUpdate,
  GoalContribution,
  GoalContributionCreate,
  GoalsResponse,
  GoalStats,
  GoalFilters,
  GoalTypeOption,
  PriorityOption
} from '../types/goals';

export class GoalService extends BaseService {
  protected baseEndpoint = '/goals';

  // Goal CRUD operations
  async createGoal(goalData: GoalCreate): Promise<Goal> {
    return apiClient.post<Goal>('/goals', goalData);
  }

  async getGoals(filters: GoalFilters = {}): Promise<GoalsResponse> {
    const params: Record<string, any> = {};
    
    if (filters.status) params.status = filters.status;
    if (filters.goal_type) params.goal_type = filters.goal_type;
    if (filters.priority) params.priority = filters.priority;
    if (filters.skip !== undefined) params.skip = filters.skip;
    if (filters.limit !== undefined) params.limit = filters.limit;

    return apiClient.get<GoalsResponse>('/goals', params);
  }

  async getGoal(goalId: string): Promise<Goal> {
    return apiClient.get<Goal>(`/goals/${goalId}`);
  }

  async updateGoal(goalId: string, goalData: GoalUpdate): Promise<Goal> {
    return apiClient.put<Goal>(`/goals/${goalId}`, goalData);
  }

  async deleteGoal(goalId: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/goals/${goalId}`);
  }

  // Contribution operations
  async addContribution(goalId: string, contributionData: GoalContributionCreate): Promise<GoalContribution> {
    return apiClient.post<GoalContribution>(`/goals/${goalId}/contributions`, contributionData);
  }

  async getGoalContributions(
    goalId: string, 
    skip: number = 0, 
    limit: number = 50
  ): Promise<GoalContribution[]> {
    return apiClient.get<GoalContribution[]>(`/goals/${goalId}/contributions`, { skip, limit });
  }

  // Analytics and statistics
  async getGoalStats(): Promise<GoalStats> {
    return apiClient.get<GoalStats>('/goals/stats');
  }

  // Utility endpoints
  async getGoalTypeOptions(): Promise<{
    goal_types: GoalTypeOption[];
    priorities: PriorityOption[];
  }> {
    return apiClient.get<{
      goal_types: GoalTypeOption[];
      priorities: PriorityOption[];
    }>('/goals/types/options');
  }


  // Helper methods for frontend calculations
  calculateProgress(currentAmount: number, targetAmount: number): number {
    if (targetAmount <= 0) return 0;
    return Math.min((currentAmount / targetAmount) * 100, 100);
  }

  calculateDaysRemaining(targetDate: string): number | null {
    if (!targetDate) return null;
    const target = new Date(targetDate);
    const now = new Date();
    const diffTime = target.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(diffDays, 0);
  }

  calculateMonthlyRequired(remainingAmount: number, daysRemaining: number | null): number | null {
    if (!daysRemaining || daysRemaining <= 0) return null;
    const monthsRemaining = daysRemaining / 30.44; // Average days per month
    return remainingAmount / monthsRemaining;
  }

  getGoalTypeInfo(type: GoalType): { label: string; icon: string; color: string } {
    const typeMap: Record<GoalType, { label: string; icon: string; color: string }> = {
      [GoalType.SAVINGS]: { label: 'Savings', icon: '💰', color: 'green' },
      [GoalType.DEBT_PAYOFF]: { label: 'Debt Payoff', icon: '💳', color: 'red' },
      [GoalType.EMERGENCY_FUND]: { label: 'Emergency Fund', icon: '🚨', color: 'orange' },
      [GoalType.INVESTMENT]: { label: 'Investment', icon: '📈', color: 'blue' },
      [GoalType.PURCHASE]: { label: 'Purchase', icon: '🛍️', color: 'purple' },
      [GoalType.OTHER]: { label: 'Other', icon: '🎯', color: 'gray' }
    };
    return typeMap[type] || typeMap[GoalType.OTHER];
  }

  getPriorityInfo(priority: GoalPriority): { label: string; color: string } {
    const priorityMap: Record<GoalPriority, { label: string; color: string }> = {
      [GoalPriority.LOW]: { label: 'Low', color: 'gray' },
      [GoalPriority.MEDIUM]: { label: 'Medium', color: 'blue' },
      [GoalPriority.HIGH]: { label: 'High', color: 'orange' },
      [GoalPriority.CRITICAL]: { label: 'Critical', color: 'red' }
    };
    return priorityMap[priority] || priorityMap[GoalPriority.MEDIUM];
  }

  getStatusInfo(status: GoalStatus): { label: string; color: string; icon: string } {
    const statusMap: Record<GoalStatus, { label: string; color: string; icon: string }> = {
      [GoalStatus.ACTIVE]: { label: 'Active', color: 'green', icon: '🎯' },
      [GoalStatus.COMPLETED]: { label: 'Completed', color: 'blue', icon: '✅' },
      [GoalStatus.PAUSED]: { label: 'Paused', color: 'yellow', icon: '⏸️' },
      [GoalStatus.CANCELLED]: { label: 'Cancelled', color: 'red', icon: '❌' }
    };
    return statusMap[status] || statusMap[GoalStatus.ACTIVE];
  }

  formatCelebrationMessage(goalName: string, percentage: number): string {
    const messages: Record<number, string> = {
      25: `🎉 Great start! You're 25% of the way to '${goalName}'!`,
      50: `🚀 Halfway there! You've reached 50% of '${goalName}'!`,
      75: `💪 Almost there! You're 75% complete with '${goalName}'!`,
      100: `🎊 Congratulations! You've achieved your goal: '${goalName}'!`
    };
    return messages[percentage] || `Milestone reached: ${percentage}% of '${goalName}'`;
  }
}

export const goalService = new GoalService();