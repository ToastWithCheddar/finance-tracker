import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { plaidService, type PlaidExchangeTokenRequest, type SyncTransactionsRequest, type SyncBalancesRequest } from '../services/plaidService';
import type { ErrorContext } from '../types/errors';
import { useAuthUser } from '../stores/authStore';

// Query keys
const PLAID_KEYS = {
  all: ['plaid'] as const,
  linkToken: (userId?: string) => [...PLAID_KEYS.all, 'link-token', userId] as const,
  connectionStatus: (userId?: string) => [...PLAID_KEYS.all, 'connection-status', userId] as const,
} as const;

// Get Plaid Link token
export function usePlaidLinkToken(
  enabled: boolean = false,
  options?: { context?: ErrorContext }
) {
  const user = useAuthUser();
  
  return useQuery({
    queryKey: PLAID_KEYS.linkToken(user?.id),
    queryFn: () => plaidService.createLinkToken(options),
    enabled: enabled && !!user?.id,
    staleTime: 5 * 60 * 1000, // 5 minutes (tokens expire in ~30 minutes)
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
  });
}

// Get connection status
export function usePlaidConnectionStatus(
  options?: { useCache?: boolean; context?: ErrorContext }
) {
  const user = useAuthUser();
  
  return useQuery({
    queryKey: PLAID_KEYS.connectionStatus(user?.id),
    queryFn: () => plaidService.getConnectionStatus(options),
    enabled: !!user?.id,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Exchange public token for access token
export function useExchangeToken() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (exchangeData: PlaidExchangeTokenRequest) => 
      plaidService.exchangeToken(exchangeData),
    onSuccess: () => {
      // Invalidate connection status and transaction-related queries
      queryClient.invalidateQueries({ queryKey: PLAID_KEYS.connectionStatus(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Sync transactions
export function useSyncTransactions() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (request?: SyncTransactionsRequest) => plaidService.syncTransactions(request),
    onSuccess: () => {
      // Invalidate transaction-related queries
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      // Invalidate connection status to update health indicators
      queryClient.invalidateQueries({ queryKey: PLAID_KEYS.connectionStatus(user?.id) });
    },
  });
}

// Sync balances
export function useSyncBalances() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (request?: SyncBalancesRequest) => plaidService.syncBalances(request),
    onSuccess: () => {
      // Invalidate account and dashboard queries
      queryClient.invalidateQueries({ queryKey: PLAID_KEYS.connectionStatus(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Combined Plaid actions hook
export function usePlaidActions() {
  const exchangeMutation = useExchangeToken();
  const syncTransactionsMutation = useSyncTransactions();
  const syncBalancesMutation = useSyncBalances();

  return {
    // Exchange token
    exchangeToken: exchangeMutation.mutate,
    
    // Sync operations  
    syncTransactions: syncTransactionsMutation.mutate,
    syncBalances: syncBalancesMutation.mutate,
    
    // Loading states
    isExchanging: exchangeMutation.isPending,
    isSyncingTransactions: syncTransactionsMutation.isPending,
    isSyncingBalances: syncBalancesMutation.isPending,
    
    // Errors
    exchangeError: exchangeMutation.error,
    syncTransactionsError: syncTransactionsMutation.error,
    syncBalancesError: syncBalancesMutation.error,
    
    // Success data
    exchangeResult: exchangeMutation.data,
    syncTransactionsResult: syncTransactionsMutation.data,
    syncBalancesResult: syncBalancesMutation.data,
  };
}