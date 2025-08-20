import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { plaidRecurringService } from '../services/plaidRecurringService';
import type {
  PlaidRecurringFilter,
  PlaidRecurringBulkMuteRequest
} from '../types/plaidRecurring';

// Query Keys
export const plaidRecurringQueryKeys = {
  all: ['plaidRecurring'] as const,
  transactions: (filters?: PlaidRecurringFilter) => [...plaidRecurringQueryKeys.all, 'transactions', filters] as const,
  transaction: (id: string) => [...plaidRecurringQueryKeys.all, 'transaction', id] as const,
  insights: () => [...plaidRecurringQueryKeys.all, 'insights'] as const,
  stats: () => [...plaidRecurringQueryKeys.all, 'stats'] as const,
  potentialMatches: (id: string) => [...plaidRecurringQueryKeys.all, 'potentialMatches', id] as const,
};

// Data fetching hooks
export const usePlaidRecurringTransactions = (filters?: PlaidRecurringFilter, enabled = true) => {
  return useQuery({
    queryKey: plaidRecurringQueryKeys.transactions(filters),
    queryFn: () => plaidRecurringService.getPlaidRecurringTransactions(filters),
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 2,
  });
};

export const usePlaidRecurringTransaction = (plaidRecurringId: string, enabled = true) => {
  return useQuery({
    queryKey: plaidRecurringQueryKeys.transaction(plaidRecurringId),
    queryFn: () => plaidRecurringService.getPlaidRecurringTransaction(plaidRecurringId),
    enabled: enabled && !!plaidRecurringId,
    staleTime: 2 * 60 * 1000,
  });
};

export const usePlaidRecurringInsights = (enabled = true) => {
  return useQuery({
    queryKey: plaidRecurringQueryKeys.insights(),
    queryFn: plaidRecurringService.getRecurringInsights,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const usePlaidRecurringStats = (enabled = true) => {
  return useQuery({
    queryKey: plaidRecurringQueryKeys.stats(),
    queryFn: plaidRecurringService.getRecurringStats,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
};

export const usePlaidRecurringPotentialMatches = (plaidRecurringId: string, enabled = true) => {
  return useQuery({
    queryKey: plaidRecurringQueryKeys.potentialMatches(plaidRecurringId),
    queryFn: () => plaidRecurringService.findPotentialMatches(plaidRecurringId),
    enabled: enabled && !!plaidRecurringId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Mutation hooks
export const useSyncPlaidRecurring = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: plaidRecurringService.syncPlaidRecurringTransactions,
    onSuccess: (result) => {
      // Invalidate all Plaid recurring data
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.all });
      
      if (result.success) {
        toast.success(
          `Sync completed! Found ${result.new_recurring_transactions} new and updated ${result.updated_recurring_transactions} recurring transactions.`
        );
      } else {
        toast.error(result.error || 'Sync completed with errors');
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to sync recurring transactions');
    },
  });
};

export const useMutePlaidRecurring = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ plaidRecurringId, muted }: { plaidRecurringId: string; muted: boolean }) =>
      plaidRecurringService.mutePlaidRecurringTransaction(plaidRecurringId, muted),
    onSuccess: (updatedTransaction, { muted }) => {
      // Update specific transaction in cache
      queryClient.setQueryData(
        plaidRecurringQueryKeys.transaction(updatedTransaction.plaid_recurring_transaction_id),
        updatedTransaction
      );
      
      // Invalidate transactions list to reflect changes
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.transactions() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.insights() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.stats() });
      
      toast.success(`Subscription ${muted ? 'muted' : 'unmuted'} successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update subscription');
    },
  });
};

export const useLinkPlaidRecurringToRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ plaidRecurringId, ruleId }: { plaidRecurringId: string; ruleId: string }) =>
      plaidRecurringService.linkPlaidRecurringToRule(plaidRecurringId, ruleId),
    onSuccess: (result) => {
      // Update specific transaction in cache
      queryClient.setQueryData(
        plaidRecurringQueryKeys.transaction(result.plaid_recurring.plaid_recurring_transaction_id),
        result.plaid_recurring
      );
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.transactions() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.insights() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.stats() });
      
      toast.success('Subscription linked to rule successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to link subscription to rule');
    },
  });
};

export const useUnlinkPlaidRecurringFromRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: plaidRecurringService.unlinkPlaidRecurringFromRule,
    onSuccess: (updatedTransaction) => {
      // Update specific transaction in cache
      queryClient.setQueryData(
        plaidRecurringQueryKeys.transaction(updatedTransaction.plaid_recurring_transaction_id),
        updatedTransaction
      );
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.transactions() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.insights() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.stats() });
      
      toast.success('Subscription unlinked from rule successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to unlink subscription from rule');
    },
  });
};

export const useBulkMutePlaidRecurring = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: plaidRecurringService.bulkMutePlaidRecurringTransactions,
    onSuccess: (result) => {
      // Invalidate all relevant queries
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.transactions() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.insights() });
      queryClient.invalidateQueries({ queryKey: plaidRecurringQueryKeys.stats() });
      
      const action = result.action;
      const successMessage = `${result.updated_count} subscriptions ${action} successfully!`;
      
      if (result.failed_count > 0) {
        toast.success(`${successMessage} ${result.failed_count} failed.`);
      } else {
        toast.success(successMessage);
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update subscriptions');
    },
  });
};

export const useExportPlaidRecurring = () => {
  return useMutation({
    mutationFn: (format: 'csv' | 'json' = 'csv') =>
      plaidRecurringService.exportPlaidRecurringTransactions(format),
    onSuccess: (blob, format) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `plaid-recurring-transactions.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Export completed successfully!');
    },
    onError: (error: any) => {
      toast.error('Failed to export recurring transactions');
    },
  });
};

// Utility hook for all Plaid recurring actions
export const usePlaidRecurringActions = () => {
  const sync = useSyncPlaidRecurring();
  const mute = useMutePlaidRecurring();
  const link = useLinkPlaidRecurringToRule();
  const unlink = useUnlinkPlaidRecurringFromRule();
  const bulkMute = useBulkMutePlaidRecurring();
  const exportData = useExportPlaidRecurring();

  return {
    sync,
    mute,
    link,
    unlink,
    bulkMute,
    exportData,
    isLoading: 
      sync.isPending ||
      mute.isPending ||
      link.isPending ||
      unlink.isPending ||
      bulkMute.isPending ||
      exportData.isPending,
  };
};