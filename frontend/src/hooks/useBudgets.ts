import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { budgetService } from '../services/budgetService';
import type { BudgetFilters, CreateBudgetRequest, UpdateBudgetRequest } from '../types/budgets';
import { queryKeys } from '../services/queryClient';

const budgetKeys = queryKeys.budgets;

// Get budgets with filters
export function useBudgets(filters?: BudgetFilters) {
  return useQuery({
    queryKey: budgetKeys.list(filters),
    queryFn: () => budgetService.getBudgets(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Get single budget
export function useBudget(budgetId: string) {
  return useQuery({
    queryKey: budgetKeys.detail(budgetId),
    queryFn: () => budgetService.getBudget(budgetId),
    enabled: !!budgetId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Get budget progress
export function useBudgetProgress(budgetId: string) {
  return useQuery({
    queryKey: budgetKeys.progress(budgetId),
    queryFn: () => budgetService.getBudgetProgress(budgetId),
    enabled: !!budgetId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Get budget summary
export function useBudgetSummary() {
  return useQuery({
    queryKey: budgetKeys.summary(),
    queryFn: () => budgetService.getBudgetSummary(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Get budget alerts
export function useBudgetAlerts() {
  return useQuery({
    queryKey: budgetKeys.alerts(),
    queryFn: () => budgetService.getBudgetAlerts(),
    staleTime: 1 * 60 * 1000, // 1 minute (alerts should be fresh)
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

// Get budget calendar
export function useBudgetCalendar(budgetId: string, month: string) {
  return useQuery({
    queryKey: [...budgetKeys.detail(budgetId), 'calendar', month],
    queryFn: () => budgetService.getBudgetCalendar(budgetId, month),
    enabled: !!budgetId && !!month,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Create budget mutation
export function useCreateBudget() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (budget: CreateBudgetRequest) => budgetService.createBudget(budget),
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.summary() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.alerts() });
    },
  });
}

// Update budget mutation
export function useUpdateBudget() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ budgetId, budget }: { budgetId: string; budget: UpdateBudgetRequest }) =>
      budgetService.updateBudget(budgetId, budget),
    onSuccess: (updatedBudget) => {
      // Update the specific budget in cache
      queryClient.setQueryData(
        budgetKeys.detail(updatedBudget.id),
        updatedBudget
      );
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.summary() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.alerts() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.progress(updatedBudget.id) });
    },
  });
}

// Delete budget mutation
export function useDeleteBudget() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (budgetId: string) => budgetService.deleteBudget(budgetId),
    onSuccess: (_, budgetId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: budgetKeys.detail(budgetId) });
      queryClient.removeQueries({ queryKey: budgetKeys.progress(budgetId) });
      
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.summary() });
      queryClient.invalidateQueries({ queryKey: budgetKeys.alerts() });
    },
  });
}

// Utility hooks
export function useBudgetActions() {
  const createMutation = useCreateBudget();
  const updateMutation = useUpdateBudget();
  const deleteMutation = useDeleteBudget();

  return {
    create: createMutation.mutate,
    update: updateMutation.mutate,
    delete: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    createError: createMutation.error,
    updateError: updateMutation.error,
    deleteError: deleteMutation.error,
  };
}