import { apiClient } from './api';
import { BaseService } from './base/BaseService';
import type { ServiceResponse } from './base/BaseService';
import type { 
  BudgetAlertSettings,
  CreateBudgetAlertSettingsRequest,
  UpdateBudgetAlertSettingsRequest,
  BudgetAlertPreview,
  BudgetAlertTest
} from '../types/budgets';

class BudgetAlertService extends BaseService {
  protected readonly baseEndpoint = '/budgets';

  // Get alert settings for a budget
  async getBudgetAlertSettings(budgetId: string): Promise<BudgetAlertSettings> {
    return apiClient.get<BudgetAlertSettings>(`${this.baseEndpoint}/${budgetId}/alert-settings`);
  }

  // Create alert settings for a budget
  async createBudgetAlertSettings(
    budgetId: string, 
    settings: CreateBudgetAlertSettingsRequest
  ): Promise<BudgetAlertSettings> {
    return apiClient.post<BudgetAlertSettings>(`${this.baseEndpoint}/${budgetId}/alert-settings`, settings);
  }

  // Update alert settings for a budget
  async updateBudgetAlertSettings(
    budgetId: string, 
    settings: UpdateBudgetAlertSettingsRequest
  ): Promise<BudgetAlertSettings> {
    return apiClient.put<BudgetAlertSettings>(`${this.baseEndpoint}/${budgetId}/alert-settings`, settings);
  }

  // Delete alert settings for a budget
  async deleteBudgetAlertSettings(budgetId: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`${this.baseEndpoint}/${budgetId}/alert-settings`);
  }

  // Preview alert for testing
  async previewBudgetAlert(budgetId: string, params: {
    budgetId: string;
    testThreshold: number;
    testAmountCents: number;
  }): Promise<BudgetAlertPreview> {
    return apiClient.post<BudgetAlertPreview>(`${this.baseEndpoint}/${budgetId}/alert-settings/preview`, {
      test_threshold: params.testThreshold,
      test_amount_cents: params.testAmountCents
    });
  }

  // Send test alert
  async sendTestBudgetAlert(budgetId: string, testData: BudgetAlertTest): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`${this.baseEndpoint}/${budgetId}/alert-settings/test`, testData);
  }

  // Wrapped versions for consistency
  async getBudgetAlertSettingsWithWrapper(budgetId: string): Promise<ServiceResponse<BudgetAlertSettings>> {
    try {
      const data = await this.getBudgetAlertSettings(budgetId);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (_error) {
      return {
        success: false,
        data: {
          id: '',
          budget_id: budgetId,
          user_id: '',
          alerts_enabled: false,
          alert_thresholds: [0.8],
          alert_frequency: 'immediate',
          suppress_repeated_alerts: false,
          end_of_period_warning: false,
          end_warning_days: 3,
          smart_pacing_alerts: false,
          milestone_celebration: false,
          created_at: '',
          updated_at: ''
        }
      } as ServiceResponse<BudgetAlertSettings>;
    }
  }

  async createBudgetAlertSettingsWithWrapper(
    budgetId: string, 
    settings: CreateBudgetAlertSettingsRequest
  ): Promise<ServiceResponse<BudgetAlertSettings>> {
    try {
      const data = await this.createBudgetAlertSettings(budgetId, settings);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      throw error;
    }
  }

  async updateBudgetAlertSettingsWithWrapper(
    budgetId: string, 
    settings: UpdateBudgetAlertSettingsRequest
  ): Promise<ServiceResponse<BudgetAlertSettings>> {
    try {
      const data = await this.updateBudgetAlertSettings(budgetId, settings);
      return {
        success: true,
        data,
        metadata: { timestamp: new Date().toISOString() }
      };
    } catch (error) {
      throw error;
    }
  }

  // Helper methods
  getDefaultAlertSettings(budgetId: string): CreateBudgetAlertSettingsRequest {
    return {
      alerts_enabled: true,
      alert_thresholds: [0.5, 0.8, 0.95],
      alert_frequency: 'immediate',
      suppress_repeated_alerts: true,
      end_of_period_warning: true,
      end_warning_days: 3,
      smart_pacing_alerts: true,
      milestone_celebration: false
    };
  }

  formatAlertThreshold(threshold: number): string {
    return `${(threshold * 100).toFixed(0)}%`;
  }

  validateAlertThresholds(thresholds: number[]): boolean {
    return thresholds.every(t => t > 0 && t <= 1) && 
           thresholds.length > 0 && 
           thresholds.length <= 10;
  }

  getAlertFrequencyDisplayName(frequency: string): string {
    switch (frequency) {
      case 'immediate': return 'Immediate';
      case 'daily': return 'Daily Digest';
      case 'weekly': return 'Weekly Summary';
      default: return frequency;
    }
  }

  // Static helper for UI components
  static getPredefinedThresholds(): Array<{ value: number; label: string; color: string }> {
    const values = [0.5, 0.75, 0.8, 0.9, 0.95];
    const colorFor = (v: number) => {
      if (v >= 0.95) return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
      if (v >= 0.9) return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
      if (v >= 0.8) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
      if (v >= 0.75) return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    };
    return values.map(v => ({
      value: v,
      label: `${(v * 100).toFixed(0)}%`,
      color: colorFor(v),
    }));
  }
}

export const budgetAlertService = new BudgetAlertService();
export { BudgetAlertService };
