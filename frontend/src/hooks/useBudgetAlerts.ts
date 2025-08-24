import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { budgetAlertService } from '../services/budgetAlertService';
import { queryKeys } from '../services/queryClient';
import type { 
  BudgetAlertSettings,
  CreateBudgetAlertSettingsRequest,
  UpdateBudgetAlertSettingsRequest,
  BudgetAlertPreview,
  BudgetAlertTest
} from '../types/budgets';

const budgetKeys = queryKeys.budgets;

// Get budget alert settings
export function useBudgetAlertSettings(budgetId: string) {
  return useQuery({
    queryKey: [...budgetKeys.detail(budgetId), 'alert-settings'],
    queryFn: () => budgetAlertService.getBudgetAlertSettings(budgetId),
    enabled: !!budgetId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Create budget alert settings mutation
export function useCreateBudgetAlertSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ budgetId, settings }: { 
      budgetId: string; 
      settings: CreateBudgetAlertSettingsRequest 
    }) => budgetAlertService.createBudgetAlertSettings(budgetId, settings),
    onSuccess: (updatedSettings, { budgetId }) => {
      // Update the specific alert settings in cache
      queryClient.setQueryData(
        [...budgetKeys.detail(budgetId), 'alert-settings'],
        updatedSettings
      );
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) });
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() });
    },
  });
}

// Update budget alert settings mutation
export function useUpdateBudgetAlertSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ budgetId, settings }: { 
      budgetId: string; 
      settings: UpdateBudgetAlertSettingsRequest 
    }) => budgetAlertService.updateBudgetAlertSettings(budgetId, settings),
    onSuccess: (updatedSettings, { budgetId }) => {
      // Update the specific alert settings in cache
      queryClient.setQueryData(
        [...budgetKeys.detail(budgetId), 'alert-settings'],
        updatedSettings
      );
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) });
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() });
    },
  });
}

// Delete budget alert settings mutation
export function useDeleteBudgetAlertSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (budgetId: string) => budgetAlertService.deleteBudgetAlertSettings(budgetId),
    onSuccess: (_, budgetId) => {
      // Remove from cache
      queryClient.removeQueries({ 
        queryKey: [...budgetKeys.detail(budgetId), 'alert-settings'] 
      });
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: budgetKeys.detail(budgetId) });
      queryClient.invalidateQueries({ queryKey: budgetKeys.lists() });
    },
  });
}

// Preview budget alert mutation
export function usePreviewBudgetAlert() {
  return useMutation({
    mutationFn: ({ budgetId, params }: { 
      budgetId: string; 
      params: {
        budgetId: string;
        testThreshold: number;
        testAmountCents: number;
      }
    }) => budgetAlertService.previewBudgetAlert(budgetId, params),
  });
}

// Send test budget alert mutation
export function useSendTestBudgetAlert() {
  return useMutation({
    mutationFn: ({ budgetId, testData }: { 
      budgetId: string; 
      testData: BudgetAlertTest 
    }) => budgetAlertService.sendTestBudgetAlert(budgetId, testData),
  });
}

// Utility hook for budget alert actions
export function useBudgetAlertActions() {
  const createMutation = useCreateBudgetAlertSettings();
  const updateMutation = useUpdateBudgetAlertSettings();
  const deleteMutation = useDeleteBudgetAlertSettings();
  const previewMutation = usePreviewBudgetAlert();
  const testMutation = useSendTestBudgetAlert();

  return {
    // CRUD operations
    create: createMutation.mutate,
    update: updateMutation.mutate,
    delete: deleteMutation.mutate,
    
    // Test and preview operations
    preview: previewMutation.mutate,
    sendTest: testMutation.mutate,
    
    // Loading states
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isPreviewing: previewMutation.isPending,
    isTesting: testMutation.isPending,
    
    // Error states
    createError: createMutation.error,
    updateError: updateMutation.error,
    deleteError: deleteMutation.error,
    previewError: previewMutation.error,
    testError: testMutation.error,
    
    // Data states
    previewData: previewMutation.data,
    testData: testMutation.data,
    
    // Reset functions
    resetPreview: previewMutation.reset,
    resetTest: testMutation.reset,
  };
}