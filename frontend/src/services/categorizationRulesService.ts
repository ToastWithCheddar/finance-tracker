import { api } from './api';
import type {
  CategorizationRule,
  CategorizationRuleCreate,
  CategorizationRuleUpdate,
  CategorizationRuleFilter,
  PaginatedCategorizationRulesResponse,
  CategorizationRuleTemplate,
  RuleTemplateCustomization,
  RuleTestResult,
  RuleApplicationResult,
  BatchRuleApplicationResult,
  RuleEffectivenessMetrics,
  RuleStatistics,
  CategorizationRuleConditions
} from '../types/categorizationRules';

export const categorizationRulesService = {
  /**
   * Get paginated categorization rules with filtering
   */
  getCategorizationRules: async (
    page = 1,
    perPage = 20,
    filters?: CategorizationRuleFilter
  ): Promise<PaginatedCategorizationRulesResponse> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('per_page', perPage.toString());
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, value.toString());
        }
      });
    }
    
    return api.get<PaginatedCategorizationRulesResponse>(`/categorization-rules?${params.toString()}`);
  },

  /**
   * Get a specific categorization rule by ID
   */
  getCategorizationRule: async (ruleId: string): Promise<CategorizationRule> => {
    return api.get<CategorizationRule>(`/categorization-rules/${ruleId}`);
  },

  /**
   * Create a new categorization rule
   */
  createCategorizationRule: async (rule: CategorizationRuleCreate): Promise<CategorizationRule> => {
    return api.post<CategorizationRule>('/categorization-rules', rule as unknown as Record<string, unknown>);
  },

  /**
   * Update an existing categorization rule
   */
  updateCategorizationRule: async (
    ruleId: string,
    updates: CategorizationRuleUpdate
  ): Promise<CategorizationRule> => {
    return api.put<CategorizationRule>(
      `/categorization-rules/${ruleId}`,
      updates as unknown as Record<string, unknown>
    );
  },

  /**
   * Delete a categorization rule
   */
  deleteCategorizationRule: async (ruleId: string): Promise<void> => {
    return api.delete<void>(`/categorization-rules/${ruleId}`);
  },

  /**
   * Test rule conditions against historical transactions
   */
  testRuleConditions: async (
    conditions: CategorizationRuleConditions,
    limit = 100
  ): Promise<RuleTestResult[]> => {
    return api.post<RuleTestResult[]>(
      `/categorization-rules/test-conditions?limit=${limit}`,
      conditions as unknown as Record<string, unknown>
    );
  },

  /**
   * Apply rules to specific transactions
   */
  applyRulesToTransactions: async (
    transactionIds: string[],
    dryRun = false
  ): Promise<BatchRuleApplicationResult> => {
    return api.post<BatchRuleApplicationResult>(
      `/categorization-rules/apply-to-transactions?dry_run=${dryRun}`,
      { transaction_ids: transactionIds }
    );
  },

  /**
   * Get available rule templates
   */
  getRuleTemplates: async (): Promise<CategorizationRuleTemplate[]> => {
    return api.get<CategorizationRuleTemplate[]>('/categorization-rules/templates');
  },

  /**
   * Create a rule from a template
   */
  createRuleFromTemplate: async (
    templateId: string,
    customizations: RuleTemplateCustomization
  ): Promise<CategorizationRule> => {
    return api.post<CategorizationRule>(
      `/categorization-rules/templates/${templateId}/create-rule`,
      { customizations } as unknown as Record<string, unknown>
    );
  },

  /**
   * Get rule statistics and analytics
   */
  getRuleStatistics: async (): Promise<RuleStatistics> => {
    return api.get<RuleStatistics>('/categorization-rules/statistics');
  },

  /**
   * Get effectiveness metrics for a specific rule
   */
  getRuleEffectiveness: async (ruleId: string): Promise<RuleEffectivenessMetrics> => {
    return api.get<RuleEffectivenessMetrics>(`/categorization-rules/${ruleId}/effectiveness`);
  },

  /**
   * Provide feedback on rule effectiveness
   */
  provideRuleFeedback: async (ruleId: string, success: boolean): Promise<void> => {
    return api.post<void>(`/categorization-rules/${ruleId}/feedback?success=${success}`, {});
  },

  /**
   * Export categorization rules
   */
  exportRules: async (format: 'json' = 'json'): Promise<Blob> => {
    const response = await fetch(`/api/categorization-rules/export?format=${format}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Export failed');
    }
    
    return response.blob();
  },

  /**
   * Import categorization rules
   */
  importRules: async (file: File): Promise<{ imported: number; failed: number; errors: string[] }> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/categorization-rules/import', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Import failed');
    }
    
    return response.json();
  },

  /**
   * Reorder rules by priority
   */
  reorderRules: async (ruleOrders: { id: string; priority: number }[]): Promise<void> => {
    return api.post<void>('/categorization-rules/reorder', { rules: ruleOrders });
  },

  /**
   * Duplicate a rule
   */
  duplicateRule: async (ruleId: string, newName?: string): Promise<CategorizationRule> => {
    return api.post<CategorizationRule>(
      `/categorization-rules/${ruleId}/duplicate`,
      { new_name: newName } as unknown as Record<string, unknown>
    );
  }
};