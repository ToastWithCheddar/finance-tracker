import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { accountService, type Account, type AccountCreate, type AccountUpdate } from '../services/accountService';
import type { ErrorContext } from '../types/errors';
import { useAuthUser } from '../stores/authStore';

// Query keys
// Hierarchical caching caching systems
const ACCOUNT_KEYS = {
  all: ['accounts'] as const,
  lists: () => [...ACCOUNT_KEYS.all, 'list'] as const,
  list: (userId?: string) => [...ACCOUNT_KEYS.lists(), userId] as const,
  details: () => [...ACCOUNT_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...ACCOUNT_KEYS.details(), id] as const,
} as const;

// Get all user accounts
export function useAccounts(
  options?: { useCache?: boolean; context?: ErrorContext }
) {
  const user = useAuthUser();
  
  return useQuery({
    queryKey: ACCOUNT_KEYS.list(user?.id),
    queryFn: () => accountService.getAccounts(options),
    enabled: !!user?.id,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes
    retry: 2,
  });
}

// Get single account
export function useAccount(
  accountId: string,
  options?: { enabled?: boolean; context?: ErrorContext }
) {
  return useQuery({
    queryKey: ACCOUNT_KEYS.detail(accountId),
    queryFn: () => accountService.getAccount(accountId, options),
    enabled: options?.enabled !== false && !!accountId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Create account mutation
export function useCreateAccount() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (accountData: AccountCreate) => 
      accountService.createAccount(accountData),
    onSuccess: () => {
      // Invalidate and refetch accounts list
      queryClient.invalidateQueries({ queryKey: ACCOUNT_KEYS.list(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Update account mutation
export function useUpdateAccount() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AccountUpdate }) => 
      accountService.updateAccount(id, data),
    onSuccess: (updatedAccount) => {
      // Update the specific account in cache
      queryClient.setQueryData(
        ACCOUNT_KEYS.detail(updatedAccount.id),
        updatedAccount
      );
      
      // Invalidate accounts list to reflect changes
      queryClient.invalidateQueries({ queryKey: ACCOUNT_KEYS.list(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Delete account mutation
export function useDeleteAccount() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (accountId: string) => accountService.deleteAccount(accountId),
    onSuccess: (_, accountId) => {
      // Remove account from cache
      queryClient.removeQueries({ queryKey: ACCOUNT_KEYS.detail(accountId) });
      
      // Invalidate accounts list
      queryClient.invalidateQueries({ queryKey: ACCOUNT_KEYS.list(user?.id) });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Combined accounts actions hook
// Instead of using three separate hooks in a component, you
// can use just one and get everything you need.
export function useAccountActions() {
  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount();
  const deleteMutation = useDeleteAccount();

  return {
    // Create
    createAccount: createMutation.mutate,
    isCreating: createMutation.isPending,
    createError: createMutation.error,
    createResult: createMutation.data,
    
    // Update
    updateAccount: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,
    updateResult: updateMutation.data,
    
    // Delete
    deleteAccount: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,
    
    // Loading states
    isLoading: createMutation.isPending || updateMutation.isPending || deleteMutation.isPending,
  };
}

// Utility hooks
export function usePlaidConnectedAccounts() {
  const { data: accounts, ...rest } = useAccounts();
  
  return {
    ...rest,
    data: accounts?.filter(account => !!account.plaid_account_id) || []
  };
}

export function useManualAccounts() {
  const { data: accounts, ...rest } = useAccounts();
  
  return {
    ...rest,
    data: accounts?.filter(account => !account.plaid_account_id) || []
  };
}

export function useAccountsByType(accountType?: string) {
  const { data: accounts, ...rest } = useAccounts();
  
  return {
    ...rest,
    data: accountType 
      ? accounts?.filter(account => account.account_type === accountType) || []
      : accounts || []
  };
}

// Export query keys for manual cache management
export { ACCOUNT_KEYS };