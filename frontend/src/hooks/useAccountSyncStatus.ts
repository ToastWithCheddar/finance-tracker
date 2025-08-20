import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { accountService, type ConnectionStatus } from '../services/accountService';

// Query keys for sync status
const syncStatusKeys = {
  connectionStatus: ['accounts', 'connection-status'] as const,
} as const;

/**
 * Hook for managing account sync status and operations
 */
export function useAccountSyncStatus() {
  const queryClient = useQueryClient();

  // Get connection status query
  const connectionStatusQuery = useQuery({
    queryKey: syncStatusKeys.connectionStatus,
    queryFn: () => accountService.getConnectionStatus(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });

  // Sync all balances mutation
  const syncAllBalancesMutation = useMutation({
    mutationFn: () => accountService.syncAllBalances(),
    onSuccess: () => {
      // Invalidate connection status and accounts data
      queryClient.invalidateQueries({ queryKey: syncStatusKeys.connectionStatus });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  // Sync single account balance mutation
  const syncAccountBalanceMutation = useMutation({
    mutationFn: (accountId: string) => accountService.syncAccountBalance(accountId),
    onSuccess: () => {
      // Invalidate connection status and accounts data
      queryClient.invalidateQueries({ queryKey: syncStatusKeys.connectionStatus });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  return {
    // Connection status data
    connectionStatus: connectionStatusQuery.data,
    isLoadingConnectionStatus: connectionStatusQuery.isLoading,
    connectionStatusError: connectionStatusQuery.error,
    refetchConnectionStatus: connectionStatusQuery.refetch,

    // Sync operations
    syncAllBalances: syncAllBalancesMutation.mutateAsync,
    isSyncingAllBalances: syncAllBalancesMutation.isPending,
    syncAllBalancesError: syncAllBalancesMutation.error,

    syncAccountBalance: syncAccountBalanceMutation.mutateAsync,
    isSyncingAccountBalance: syncAccountBalanceMutation.isPending,
    syncAccountBalanceError: syncAccountBalanceMutation.error,

    // Reset errors
    resetSyncAllBalancesError: () => syncAllBalancesMutation.reset(),
    resetSyncAccountBalanceError: () => syncAccountBalanceMutation.reset(),
  };
}

export type { ConnectionStatus };