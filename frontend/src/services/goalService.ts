import { apiClient } from './api';
import { GoalStatus, GoalType, GoalPriority } from '../types/goals';
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
  PriorityOption,
  FrequencyOption
} from '../types/goals';

export class GoalService {
  private baseEndpoint = '/goals';

  // Goal CRUD operations
  async createGoal(goalData: GoalCreate): Promise<Goal> {
    return apiClient.post<Goal>(`${this.baseEndpoint}/`, goalData);
  }

  async getGoals(filters: GoalFilters = {}): Promise<GoalsResponse> {
    const params = new URLSearchParams();
    
    if (filters.status) params.append('status', filters.status);
    if (filters.goal_type) params.append('goal_type', filters.goal_type);
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString());

    return apiClient.get<GoalsResponse>(`${this.baseEndpoint}/?${params.toString()}`);
  }

  async getGoal(goalId: string): Promise<Goal> {
    return apiClient.get<Goal>(`${this.baseEndpoint}/${goalId}`);
  }

  async updateGoal(goalId: string, goalData: GoalUpdate): Promise<Goal> {
    return apiClient.put<Goal>(`${this.baseEndpoint}/${goalId}`, goalData);
  }

  async deleteGoal(goalId: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`${this.baseEndpoint}/${goalId}`);
  }

  // Contribution operations
  async addContribution(goalId: string, contributionData: GoalContributionCreate): Promise<GoalContribution> {
    return apiClient.post<GoalContribution>(`${this.baseEndpoint}/${goalId}/contributions`, contributionData);
  }

  async getGoalContributions(
    goalId: string, 
    skip: number = 0, 
    limit: number = 50
  ): Promise<GoalContribution[]> {
    return apiClient.get<GoalContribution[]>(`${this.baseEndpoint}/${goalId}/contributions?skip=${skip}&limit=${limit}`);
  }

  // Analytics and statistics
  async getGoalStats(): Promise<GoalStats> {
    return apiClient.get<GoalStats>(`${this.baseEndpoint}/stats`);
  }

  // Utility endpoints
  async getGoalTypeOptions(): Promise<{
    goal_types: GoalTypeOption[];
    priorities: PriorityOption[];
    frequencies: FrequencyOption[];
  }> {
    return apiClient.get<{
      goal_types: GoalTypeOption[];
      priorities: PriorityOption[];
      frequencies: FrequencyOption[];
    }>(`${this.baseEndpoint}/types/options`);
  }

  async processAutoContributions(): Promise<{
    message: string;
    results: { success: number; failed: number };
  }> {
    return apiClient.post<{
      message: string;
      results: { success: number; failed: number };
    }>(`${this.baseEndpoint}/process-auto-contributions`);
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