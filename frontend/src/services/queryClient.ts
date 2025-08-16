import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import type { GoalFilters } from '../types/goals';
import type { BudgetFilters } from '../types/budgets';

// Error handler for queries and mutations
const errorHandler = (error: unknown) => {
  const message = error instanceof Error ? error.message : 'An unexpected error occurred';
  
  // If it's an authentication error, logout the user
  if (message.includes('401') || message.includes('Unauthorized')) {
    useAuthStore.getState().logout();
  }
  
  console.error('Query/Mutation Error:', message);
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

  // User Preferences
  userPreferences: {
    all: ['user-preferences'] as const,
    current: () => [...queryKeys.userPreferences.all, 'current'] as const,
  },
} as const;