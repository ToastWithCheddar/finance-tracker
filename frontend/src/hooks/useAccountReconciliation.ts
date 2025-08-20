import { useMutation, useQueryClient } from '@tanstack/react-query';
import { accountService, type ReconciliationResult, type ReconciliationAdjustment } from '../services/accountService';

/**
 * Hook for managing account reconciliation operations
 */
export function useAccountReconciliation() {
  const queryClient = useQueryClient();

  // Perform reconciliation mutation
  const performReconciliationMutation = useMutation({
    mutationFn: (accountId: string) => accountService.performReconciliation(accountId),
    onSuccess: () => {
      // Invalidate accounts data to refresh balances
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  // Create reconciliation adjustment mutation
  const createAdjustmentMutation = useMutation({
    mutationFn: ({ accountId, adjustmentData }: { accountId: string; adjustmentData: ReconciliationAdjustment }) =>
      accountService.createReconciliationAdjustment(accountId, adjustmentData),
    onSuccess: () => {
      // Invalidate accounts and reconciliation data
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  return {
    // Perform reconciliation
    performReconciliation: performReconciliationMutation.mutateAsync,
    isPerformingReconciliation: performReconciliationMutation.isPending,
    reconciliationError: performReconciliationMutation.error,

    // Create adjustment
    createAdjustment: createAdjustmentMutation.mutateAsync,
    isCreatingAdjustment: createAdjustmentMutation.isPending,
    adjustmentError: createAdjustmentMutation.error,

    // Reset errors
    resetReconciliationError: () => performReconciliationMutation.reset(),
    resetAdjustmentError: () => createAdjustmentMutation.reset(),
  };
}

export type { ReconciliationResult, ReconciliationAdjustment };