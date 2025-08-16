import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import type {
  RecurringTransactionRule,
  RecurringSuggestion,
  RecurringRuleStats,
  RecurringTransactionRuleCreate,
  RecurringTransactionRuleUpdate,
  SuggestionApproval,
  RecurringRuleFilter,
  PaginatedRecurringRulesResponse
} from '../types/recurring';
import { api } from '../services/api';

// Query Keys
export const recurringQueryKeys = {
  all: ['recurring'] as const,
  suggestions: () => [...recurringQueryKeys.all, 'suggestions'] as const,
  rules: (filters?: RecurringRuleFilter, page?: number, perPage?: number) => 
    [...recurringQueryKeys.all, 'rules', { filters, page, perPage }] as const,
  rule: (id: string) => [...recurringQueryKeys.all, 'rule', id] as const,
  stats: () => [...recurringQueryKeys.all, 'stats'] as const,
};

// API Functions
const recurringApi = {
  getSuggestions: async (minConfidence = 0.5): Promise<RecurringSuggestion[]> => {
    const response = await api.get<RecurringSuggestion[]>(`/recurring/suggestions?min_confidence=${minConfidence}`);
    return response;
  },

  approveSuggestion: async (approval: SuggestionApproval): Promise<RecurringTransactionRule> => {
    const response = await api.post<RecurringTransactionRule>('/recurring/suggestions/approve', approval as unknown as Record<string, unknown>);
    return response;
  },

  dismissSuggestion: async (suggestionId: string): Promise<void> => {
    await api.post<void>('/recurring/suggestions/dismiss', { suggestion_id: suggestionId });
  },

  createRule: async (rule: RecurringTransactionRuleCreate): Promise<RecurringTransactionRule> => {
    const response = await api.post<RecurringTransactionRule>('/recurring/rules', rule as unknown as Record<string, unknown>);
    return response;
  },

  getRules: async (
    page = 1,
    perPage = 20,
    filters?: RecurringRuleFilter
  ): Promise<PaginatedRecurringRulesResponse> => {
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

    const response = await api.get<PaginatedRecurringRulesResponse>(`/recurring/rules?${params.toString()}`);
    return response;
  },

  getRule: async (id: string): Promise<RecurringTransactionRule> => {
    const response = await api.get<RecurringTransactionRule>(`/recurring/rules/${id}`);
    return response;
  },

  updateRule: async (
    id: string,
    updates: RecurringTransactionRuleUpdate
  ): Promise<RecurringTransactionRule> => {
    const response = await api.put<RecurringTransactionRule>(`/recurring/rules/${id}`, updates as unknown as Record<string, unknown>);
    return response;
  },

  deleteRule: async (id: string): Promise<void> => {
    await api.delete<void>(`/recurring/rules/${id}`);
  },

  getStats: async (): Promise<RecurringRuleStats> => {
    const response = await api.get<RecurringRuleStats>('/recurring/stats');
    return response;
  },
};

// Hooks
export const useRecurringSuggestions = (minConfidence = 0.5, enabled = true) => {
  return useQuery({
    queryKey: recurringQueryKeys.suggestions(),
    queryFn: () => recurringApi.getSuggestions(minConfidence),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
};

export const useRecurringRules = (
  page = 1,
  perPage = 20,
  filters?: RecurringRuleFilter,
  enabled = true
) => {
  return useQuery({
    queryKey: recurringQueryKeys.rules(filters, page, perPage),
    queryFn: () => recurringApi.getRules(page, perPage, filters),
    enabled,
    placeholderData: (previousData) => previousData, // Replace keepPreviousData
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useRecurringRule = (id: string, enabled = true) => {
  return useQuery({
    queryKey: recurringQueryKeys.rule(id),
    queryFn: () => recurringApi.getRule(id),
    enabled: enabled && !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useRecurringStats = (enabled = true) => {
  return useQuery({
    queryKey: recurringQueryKeys.stats(),
    queryFn: recurringApi.getStats,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
};

// Mutation Hooks
export const useApproveSuggestion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: recurringApi.approveSuggestion,
    onSuccess: (rule) => {
      // Invalidate and refetch suggestions and rules
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.suggestions() });
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.stats() });
      
      toast.success(`Recurring rule "${rule.name}" created successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to approve suggestion');
    },
  });
};

export const useDismissSuggestion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: recurringApi.dismissSuggestion,
    onSuccess: () => {
      // Invalidate and refetch suggestions
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.suggestions() });
      
      toast.success('Suggestion dismissed successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to dismiss suggestion');
    },
  });
};

export const useCreateRecurringRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: recurringApi.createRule,
    onSuccess: (rule) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.stats() });
      
      toast.success(`Recurring rule "${rule.name}" created successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create recurring rule');
    },
  });
};

export const useUpdateRecurringRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: RecurringTransactionRuleUpdate }) =>
      recurringApi.updateRule(id, updates),
    onSuccess: (rule) => {
      // Update cache for specific rule
      queryClient.setQueryData(recurringQueryKeys.rule(rule.id), rule);
      
      // Invalidate rules list to reflect changes
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.stats() });
      
      toast.success(`Recurring rule "${rule.name}" updated successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update recurring rule');
    },
  });
};

export const useDeleteRecurringRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: recurringApi.deleteRule,
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: recurringQueryKeys.rule(id) });
      
      // Invalidate rules list
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.rules() });
      queryClient.invalidateQueries({ queryKey: recurringQueryKeys.stats() });
      
      toast.success('Recurring rule deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete recurring rule');
    },
  });
};

// Utility hooks
export const useRecurringActions = () => {
  const approveSuggestion = useApproveSuggestion();
  const dismissSuggestion = useDismissSuggestion();
  const createRule = useCreateRecurringRule();
  const updateRule = useUpdateRecurringRule();
  const deleteRule = useDeleteRecurringRule();

  return {
    approveSuggestion,
    dismissSuggestion,
    createRule,
    updateRule,
    deleteRule,
    isLoading: 
      approveSuggestion.isPending ||
      dismissSuggestion.isPending ||
      createRule.isPending ||
      updateRule.isPending ||
      deleteRule.isPending,
  };
};