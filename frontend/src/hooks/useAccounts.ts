import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { accountService, type Account, type AccountCreate, type AccountUpdate } from '../services/accountService';
import { useAuthUser } from '../stores/authStore';

// Simple query keys
const accountKeys = {
  all: ['accounts'] as const,
  list: (userId?: string) => ['accounts', userId] as const,
  detail: (id: string) => ['accounts', 'detail', id] as const,
} as const;

// Main accounts hook - simplified
export function useAccounts() {
  const user = useAuthUser();
  
  return useQuery({
    queryKey: accountKeys.list(user?.id),
    queryFn: () => accountService.getAccounts(),
    enabled: !!user?.id,
    staleTime: 30 * 1000, // 30 seconds
  });
}

// Single account
export function useAccount(accountId: string, enabled = true) {
  return useQuery({
    queryKey: accountKeys.detail(accountId),
    queryFn: () => accountService.getAccount(accountId),
    enabled: enabled && !!accountId,
    staleTime: 30 * 1000,
  });
}

// Create account
export function useCreateAccount() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (data: AccountCreate) => accountService.createAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: accountKeys.list(user?.id) });
    },
  });
}

// Update account
export function useUpdateAccount() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AccountUpdate }) => 
      accountService.updateAccount(id, data),
    onSuccess: (updatedAccount) => {
      queryClient.setQueryData(accountKeys.detail(updatedAccount.id), updatedAccount);
      queryClient.invalidateQueries({ queryKey: accountKeys.list(user?.id) });
    },
  });
}

// Delete account
export function useDeleteAccount() {
  const queryClient = useQueryClient();
  const user = useAuthUser();

  return useMutation({
    mutationFn: (accountId: string) => accountService.deleteAccount(accountId),
    onSuccess: (_, accountId) => {
      queryClient.removeQueries({ queryKey: accountKeys.detail(accountId) });
      queryClient.invalidateQueries({ queryKey: accountKeys.list(user?.id) });
    },
  });
}