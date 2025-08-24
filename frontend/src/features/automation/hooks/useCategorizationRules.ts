import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { categorizationRulesService } from '../services/categorizationRulesService';
import type {
  CategorizationRuleFilter,
  CategorizationRuleCreate,
  CategorizationRuleUpdate,
  RuleTemplateCustomization,
  CategorizationRuleConditions
} from '../types/categorizationRules';

// Query Keys
export const categorizationRulesQueryKeys = {
  all: ['categorizationRules'] as const,
  rules: (filters?: CategorizationRuleFilter, page?: number, perPage?: number) => 
    [...categorizationRulesQueryKeys.all, 'rules', { filters, page, perPage }] as const,
  rule: (id: string) => [...categorizationRulesQueryKeys.all, 'rule', id] as const,
  templates: () => [...categorizationRulesQueryKeys.all, 'templates'] as const,
  statistics: () => [...categorizationRulesQueryKeys.all, 'statistics'] as const,
  effectiveness: (id: string) => [...categorizationRulesQueryKeys.all, 'effectiveness', id] as const,
  testResults: (conditions: CategorizationRuleConditions, limit?: number) => 
    [...categorizationRulesQueryKeys.all, 'testResults', { conditions, limit }] as const,
};

// Data fetching hooks
export const useCategorizationRules = (
  page = 1,
  perPage = 20,
  filters?: CategorizationRuleFilter,
  enabled = true
) => {
  return useQuery({
    queryKey: categorizationRulesQueryKeys.rules(filters, page, perPage),
    queryFn: () => categorizationRulesService.getCategorizationRules(page, perPage, filters),
    enabled,
    placeholderData: (previousData) => previousData,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useCategorizationRule = (ruleId: string, enabled = true) => {
  return useQuery({
    queryKey: categorizationRulesQueryKeys.rule(ruleId),
    queryFn: () => categorizationRulesService.getCategorizationRule(ruleId),
    enabled: enabled && !!ruleId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useRuleTemplates = (enabled = true) => {
  return useQuery({
    queryKey: categorizationRulesQueryKeys.templates(),
    queryFn: categorizationRulesService.getRuleTemplates,
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - templates don't change often
  });
};

export const useRuleStatistics = (enabled = true) => {
  return useQuery({
    queryKey: categorizationRulesQueryKeys.statistics(),
    queryFn: categorizationRulesService.getRuleStatistics,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useRuleEffectiveness = (ruleId: string, enabled = true) => {
  return useQuery({
    queryKey: categorizationRulesQueryKeys.effectiveness(ruleId),
    queryFn: () => categorizationRulesService.getRuleEffectiveness(ruleId),
    enabled: enabled && !!ruleId,
    staleTime: 5 * 60 * 1000,
  });
};

export const useTestRuleConditions = (
  conditions: CategorizationRuleConditions,
  limit = 100,
  enabled = false // Only run when explicitly requested
) => {
  return useQuery({
    queryKey: categorizationRulesQueryKeys.testResults(conditions, limit),
    queryFn: () => categorizationRulesService.testRuleConditions(conditions, limit),
    enabled: enabled && Object.keys(conditions).length > 0,
    staleTime: 0, // Don't cache test results
  });
};

// Mutation hooks
export const useCreateCategorizationRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: categorizationRulesService.createCategorizationRule,
    onSuccess: (rule) => {
      // Invalidate rules list to include new rule
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      toast.success(`Categorization rule "${rule.name}" created successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create categorization rule');
    },
  });
};

export const useUpdateCategorizationRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ruleId, updates }: { ruleId: string; updates: CategorizationRuleUpdate }) =>
      categorizationRulesService.updateCategorizationRule(ruleId, updates),
    onSuccess: (rule) => {
      // Update specific rule in cache
      queryClient.setQueryData(categorizationRulesQueryKeys.rule(rule.id), rule);
      
      // Invalidate rules list to reflect changes
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      toast.success(`Categorization rule "${rule.name}" updated successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update categorization rule');
    },
  });
};

export const useDeleteCategorizationRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: categorizationRulesService.deleteCategorizationRule,
    onSuccess: (_, ruleId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: categorizationRulesQueryKeys.rule(ruleId) });
      
      // Invalidate rules list
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      toast.success('Categorization rule deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete categorization rule');
    },
  });
};

export const useCreateRuleFromTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ templateId, customizations }: { templateId: string; customizations: RuleTemplateCustomization }) =>
      categorizationRulesService.createRuleFromTemplate(templateId, customizations),
    onSuccess: (rule) => {
      // Invalidate rules list to include new rule
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      toast.success(`Rule "${rule.name}" created from template successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create rule from template');
    },
  });
};

export const useApplyRulesToTransactions = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ transactionIds, dryRun }: { transactionIds: string[]; dryRun?: boolean }) =>
      categorizationRulesService.applyRulesToTransactions(transactionIds, dryRun),
    onSuccess: (result, { dryRun }) => {
      if (!dryRun) {
        // Invalidate transactions data since categorizations may have changed
        queryClient.invalidateQueries({ queryKey: ['transactions'] });
        queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
        
        const appliedCount = result.rules_applied;
        toast.success(`Successfully applied rules to ${appliedCount} transactions!`);
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to apply rules to transactions');
    },
  });
};

export const useProvideRuleFeedback = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ruleId, success }: { ruleId: string; success: boolean }) =>
      categorizationRulesService.provideRuleFeedback(ruleId, success),
    onSuccess: (_, { ruleId, success }) => {
      // Invalidate effectiveness data for the rule
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.effectiveness(ruleId) });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      toast.success(`Feedback recorded: Rule was ${success ? 'helpful' : 'not helpful'}`);
    },
    onError: (error: any) => {
      toast.error('Failed to record feedback');
    },
  });
};

export const useReorderRules = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: categorizationRulesService.reorderRules,
    onSuccess: () => {
      // Invalidate rules list to reflect new order
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      
      toast.success('Rule order updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to reorder rules');
    },
  });
};

export const useDuplicateRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ruleId, newName }: { ruleId: string; newName?: string }) =>
      categorizationRulesService.duplicateRule(ruleId, newName),
    onSuccess: (rule) => {
      // Invalidate rules list to include duplicated rule
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      toast.success(`Rule duplicated as "${rule.name}"!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to duplicate rule');
    },
  });
};

export const useExportRules = () => {
  return useMutation({
    mutationFn: (format: 'json' = 'json') =>
      categorizationRulesService.exportRules(format),
    onSuccess: (blob, format) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `categorization-rules.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Rules exported successfully!');
    },
    onError: (error: any) => {
      toast.error('Failed to export rules');
    },
  });
};

export const useImportRules = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: categorizationRulesService.importRules,
    onSuccess: (result) => {
      // Invalidate rules to show imported ones
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: categorizationRulesQueryKeys.statistics() });
      
      if (result.failed > 0) {
        toast.success(`Imported ${result.imported} rules successfully. ${result.failed} failed.`);
      } else {
        toast.success(`Successfully imported ${result.imported} rules!`);
      }
    },
    onError: (error: any) => {
      toast.error('Failed to import rules');
    },
  });
};

// Utility hook for all categorization rule actions
export const useCategorizationRuleActions = () => {
  const create = useCreateCategorizationRule();
  const update = useUpdateCategorizationRule();
  const deleteRule = useDeleteCategorizationRule();
  const createFromTemplate = useCreateRuleFromTemplate();
  const applyToTransactions = useApplyRulesToTransactions();
  const provideFeedback = useProvideRuleFeedback();
  const reorder = useReorderRules();
  const duplicate = useDuplicateRule();
  const exportRules = useExportRules();
  const importRules = useImportRules();

  return {
    create,
    update,
    delete: deleteRule,
    createFromTemplate,
    applyToTransactions,
    provideFeedback,
    reorder,
    duplicate,
    export: exportRules,
    import: importRules,
    isLoading: 
      create.isPending ||
      update.isPending ||
      deleteRule.isPending ||
      createFromTemplate.isPending ||
      applyToTransactions.isPending ||
      provideFeedback.isPending ||
      reorder.isPending ||
      duplicate.isPending ||
      exportRules.isPending ||
      importRules.isPending,
  };
};