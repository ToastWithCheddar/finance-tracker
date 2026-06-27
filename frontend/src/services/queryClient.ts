import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import type { GoalFilters } from '../types/goals';
import type { BudgetFilters } from '../types/budgets';
import type { Transaction } from '../types/transaction';

// Error handler for queries and mutations
import { logger } from '../utils/logger';
const errorHandler = (error: unknown) => {
  const message = error instanceof Error ? error.message : 'An unexpected error occurred';
  
  // If it's an authentication error, logout the user
  if (message.includes('401') || message.includes('Unauthorized')) {
    useAuthStore.getState().logout();
  }
  
  logger.error('Query/Mutation Error:', message);
};

// Create query client with default configuration
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: 5 minutes
      staleTime: 5 * 60 * 1000,
      // Cache time: 10 minutes
      gcTime: 10 * 60 * 1000,
      // Retry failed requests
      retry: (failureCount, error) => {
        // Don't retry on authentication errors
        if (error instanceof Error && error.message.includes('401')) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      // Refetch on window focus
      refetchOnWindowFocus: false,
      // Refetch on reconnect
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry mutations once
      retry: 1,
    },
  },
  queryCache: new QueryCache({
    onError: errorHandler,
  }),
  mutationCache: new MutationCache({
    onError: errorHandler,
  }),
});

// Query keys factory for consistent key management
export const queryKeys = {
  // Auth
  auth: {
    user: ['auth', 'user'] as const,
  },
  
  // Transactions
  transactions: {
    all: ['transactions'] as const,
    lists: () => [...queryKeys.transactions.all, 'list'] as const,
    list: (filters?: Record<string, string | number | boolean>) => 
      [...queryKeys.transactions.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.transactions.all, 'detail', id] as const,
    summary: (filters?: Record<string, string | number | boolean>) => 
      [...queryKeys.transactions.all, 'summary', filters] as const,
  },
  
  // Categories
  categories: {
    all: ['categories'] as const,
    lists: () => [...queryKeys.categories.all, 'list'] as const,
    list: (filters?: Record<string, unknown>) => 
      [...queryKeys.categories.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.categories.all, 'detail', id] as const,
  },
  
  // Accounts
  accounts: {
    all: ['accounts'] as const,
    lists: () => [...queryKeys.accounts.all, 'list'] as const,
    list: (filters?: Record<string, unknown>) => 
      [...queryKeys.accounts.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.accounts.all, 'detail', id] as const,
  },

  budgets: {
    all: ['budgets'] as const,
    lists: () => [...queryKeys.budgets.all, 'list'] as const,
    list: (filters?: BudgetFilters) => [...queryKeys.budgets.lists(), filters] as const,
    details: () => [...queryKeys.budgets.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.budgets.details(), id] as const,
    progress: (id: string) => [...queryKeys.budgets.all, 'progress', id] as const,
    summary: () => [...queryKeys.budgets.all, 'summary'] as const,
    alerts: () => [...queryKeys.budgets.all, 'alerts'] as const,
  },

  // Goals
  goals: {
    all: ['goals'] as const,
    lists: () => [...queryKeys.goals.all, 'list'] as const,
    list: (filters: GoalFilters) => [...queryKeys.goals.lists(), filters] as const,
    details: () => [...queryKeys.goals.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.goals.details(), id] as const,
    stats: () => [...queryKeys.goals.all, 'stats'] as const,
    contributions: (goalId: string) => [...queryKeys.goals.all, 'contributions', goalId] as const,
    options: () => [...queryKeys.goals.all, 'options'] as const,
  },

  // Dashboard / aggregates
  dashboard: {
    all: ['dashboard'] as const,
    summary: () => [...queryKeys.dashboard.all, 'summary'] as const,
    transactionStats: () => ['transactions', 'stats'] as const,
    categoryBreakdown: () => ['category-breakdown'] as const,
  },
} as const;

// ==========================
// Cache Helper Utilities
// ==========================

// Invalidate dashboard-related queries (various keys used in codebase)
export function invalidateDashboard() {
  // Common dashboard keys actually in use
  queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
  queryClient.invalidateQueries({ predicate: (q) => Array.isArray(q.queryKey) && q.queryKey[0] === 'category-breakdown' });
  // Related aggregates
  queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
}

// Upsert a transaction into any cached transaction list pages where it already exists
export function upsertTransactionInCache(updated: Partial<Transaction> & { id: string }) {
  const txId = String(updated.id);
  // Get all queries under the 'transactions' namespace
  const lists = queryClient.getQueriesData<any>({ queryKey: ['transactions'] });
  lists.forEach(([key, data]) => {
    if (!data) return;
    // Support both normalized list envelopes and potential array responses
    if (Array.isArray(data)) {
      const idx = data.findIndex((t: any) => String(t?.id) === txId);
      if (idx !== -1) {
        const next = data.slice();
        next[idx] = { ...next[idx], ...updated };
        queryClient.setQueryData(key, next);
      }
      return;
    }
    if (Array.isArray(data.items)) {
      const idx = data.items.findIndex((t: any) => String(t?.id) === txId);
      if (idx !== -1) {
        const nextItems = data.items.slice();
        nextItems[idx] = { ...nextItems[idx], ...updated };
        queryClient.setQueryData(key, { ...data, items: nextItems });
      }
    }
  });
}

// Remove a transaction from any cached transaction list pages
export function removeTransactionFromCache(id: string) {
  const txId = String(id);
  const lists = queryClient.getQueriesData<any>({ queryKey: ['transactions'] });
  lists.forEach(([key, data]) => {
    if (!data) return;
    if (Array.isArray(data)) {
      const before = data.length;
      const next = data.filter((t: any) => String(t?.id) !== txId);
      if (next.length !== before) {
        queryClient.setQueryData(key, next);
      }
      return;
    }
    if (Array.isArray(data.items)) {
      const before = data.items.length;
      const nextItems = data.items.filter((t: any) => String(t?.id) !== txId);
      if (nextItems.length !== before) {
        // Leave totals/pages unchanged to avoid inconsistencies; server will correct on refetch
        queryClient.setQueryData(key, { ...data, items: nextItems });
      }
    }
  });
}
