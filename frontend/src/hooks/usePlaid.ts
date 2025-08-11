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
      // Invalidate all related queries after successful token exchange
      queryClient.invalidateQueries({ queryKey: ['accounts'] }); // Add accounts cache invalidation
      queryClient.invalidateQueries({ queryKey: PLAID_KEYS.connectionStatus(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      // Also invalidate dashboard analytics which uses a different key
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
    },
  });
}

// Sync transactions
export function useSyncTransactions() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (request?: SyncTransactionsRequest) => {
      console.log('🚀 useSyncTransactions mutation started with request:', request);
      return plaidService.syncTransactions(request);
    },
    onSuccess: (data) => {
      console.log('✅ Transaction sync successful:', JSON.stringify(data, null, 2));
      
      // Show detailed success message
      const results = data.data?.results || data.data;
      if (Array.isArray(results)) {
        console.log('📊 Processing array of results:', results.length, 'accounts');
        results.forEach((result: any, index) => {
          console.log(`   Account ${index + 1}: ${result.account_name || result.name || 'Unknown'}`);
          // Handle both possible response structures
          const txData = result.result || result;
          console.log(`     - New: ${txData.new_transactions || 0}, Updated: ${txData.updated_transactions || 0}, Skipped: ${txData.duplicates_skipped || 0}`);
          if (result.success === false && result.error) {
            console.log(`     - Error: ${result.error}`);
          }
        });
        
        const totalNew = results.reduce((sum: number, r: any) => sum + ((r.result?.new_transactions || r.new_transactions) || 0), 0);
        const totalUpdated = results.reduce((sum: number, r: any) => sum + ((r.result?.updated_transactions || r.updated_transactions) || 0), 0);
        console.log(`✨ TOTAL: ${totalNew} new, ${totalUpdated} updated transactions`);
      } else if (results) {
        console.log('📊 Processing single result:', results);
        console.log(`✨ Successfully synced: ${results.new_transactions || 0} new, ${results.updated_transactions || 0} updated transactions`);
      } else {
        console.log('⚠️ No results data found in response');
      }
      
      // Invalidate transaction-related queries
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      // Invalidate connection status to update health indicators
      queryClient.invalidateQueries({ queryKey: PLAID_KEYS.connectionStatus(user?.id) });
    },
    onError: (error) => {
      console.error('❌ Transaction sync failed:', error);
    },
    onMutate: (variables) => {
      console.log('🔄 Transaction sync starting with variables:', variables);
    },
  });
}

// Sync balances
export function useSyncBalances() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (request?: SyncBalancesRequest) => {
      console.log('🚀 useSyncBalances mutation started with request:', request);
      return plaidService.syncBalances(request);
    },
    onSuccess: (data) => {
      console.log('✅ Balance sync successful:', data);
      
      // Invalidate account and dashboard queries - balances have updated
      queryClient.invalidateQueries({ queryKey: ['accounts'] }); // Add accounts cache invalidation
      queryClient.invalidateQueries({ queryKey: PLAID_KEYS.connectionStatus(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
    },
    onError: (error) => {
      console.error('❌ Balance sync failed:', error);
    },
    onMutate: (variables) => {
      console.log('🔄 Mutation starting with variables:', variables);
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