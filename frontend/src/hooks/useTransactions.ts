import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  transactionService, 
  type TransactionFilters,
  type CSVImportResponse,
  type ExportFilters 
} from '../services/transactionService';
import type { 
  CreateTransactionRequest as TransactionCreate, 
  UpdateTransactionRequest as TransactionUpdate, 
  TransactionFilters as TransactionFilter 
} from '../types/transaction';

// Query keys
import { logger } from '../utils/logger';
const TRANSACTION_KEYS = {
  all: ['transactions'] as const,
  lists: () => [...TRANSACTION_KEYS.all, 'list'] as const,
  list: (filters?: Partial<TransactionFilters>) => [...TRANSACTION_KEYS.lists(), filters] as const,
  details: () => [...TRANSACTION_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...TRANSACTION_KEYS.details(), id] as const,
  stats: (filters?: TransactionFilter) => [...TRANSACTION_KEYS.all, 'stats', filters] as const,
} as const;

// Get transactions with filters and pagination
export function useTransactions(filters?: Partial<TransactionFilters>, enabled: boolean = true) {
  return useQuery({
    queryKey: TRANSACTION_KEYS.list(filters),
    queryFn: () => {
      return transactionService.getTransactions(filters);
    },
    enabled: enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Get grouped transactions with filters and pagination
export function useTransactionsGrouped(
  filters?: TransactionFilters & { group_by: 'date' | 'category' | 'merchant' }
) {
  return useQuery({
    queryKey: [...TRANSACTION_KEYS.lists(), 'grouped', filters],
    queryFn: () => {
      if (!filters) {
        throw new Error('Filters are required for grouped transactions');
      }
      return transactionService.getTransactionsGrouped(filters);
    },
    enabled: !!filters && !!filters.group_by,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Get single transaction
export function useTransaction(transactionId: string) {
  return useQuery({
    queryKey: TRANSACTION_KEYS.detail(transactionId),
    queryFn: () => transactionService.getTransaction(transactionId),
    enabled: !!transactionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Get transaction stats
export function useTransactionStats(filters?: TransactionFilter) {
  return useQuery({
    queryKey: TRANSACTION_KEYS.stats(filters),
    queryFn: () => transactionService.getTransactionStats(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1, // Only retry once since we now use fallback calculation
  });
}

// Create transaction mutation
export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (transaction: TransactionCreate) => transactionService.createTransaction(transaction),
    onSuccess: () => {
      // Invalidate transaction lists and stats
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.lists() });
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.all });
      // Invalidate ALL stats queries regardless of filters using predicate
      queryClient.invalidateQueries({ 
        predicate: (query) => 
          Array.isArray(query.queryKey) && 
          query.queryKey[0] === 'transactions' && 
          query.queryKey[1] === 'stats'
      });
      
      // Also invalidate budget-related queries since transactions affect budgets
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      
      // Invalidate all dashboard data including category breakdown
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['category-breakdown'] });
      
    },
  });
}

// Update transaction mutation
export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ transactionId, transaction }: { transactionId: string; transaction: TransactionUpdate }) =>
      transactionService.updateTransaction(transactionId, transaction),
    onSuccess: (updatedTransaction) => {
      // Update the specific transaction in cache
      queryClient.setQueryData(
        TRANSACTION_KEYS.detail(updatedTransaction.id.toString()),
        updatedTransaction
      );
      
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.lists() });
      // Invalidate ALL stats queries regardless of filters using predicate
      queryClient.invalidateQueries({ 
        predicate: (query) => 
          Array.isArray(query.queryKey) && 
          query.queryKey[0] === 'transactions' && 
          query.queryKey[1] === 'stats'
      });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['category-breakdown'] });
      
    },
  });
}

// Delete transaction mutation
export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (transactionId: string) => transactionService.deleteTransaction(transactionId),
    onSuccess: (_, transactionId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: TRANSACTION_KEYS.detail(transactionId) });
      
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.lists() });
      // Invalidate ALL stats queries regardless of filters using predicate
      queryClient.invalidateQueries({ 
        predicate: (query) => 
          Array.isArray(query.queryKey) && 
          query.queryKey[0] === 'transactions' && 
          query.queryKey[1] === 'stats'
      });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['category-breakdown'] });
      
    },
  });
}

// Bulk delete transactions mutation
export function useBulkDeleteTransactions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (transactionIds: string[]) => transactionService.bulkDeleteTransactions(transactionIds),
    onSuccess: (_, transactionIds) => {
      // Remove from cache
      transactionIds.forEach(id => {
        queryClient.removeQueries({ queryKey: TRANSACTION_KEYS.detail(id) });
      });
      
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.lists() });
      // Invalidate ALL stats queries regardless of filters using predicate
      queryClient.invalidateQueries({ 
        predicate: (query) => 
          Array.isArray(query.queryKey) && 
          query.queryKey[0] === 'transactions' && 
          query.queryKey[1] === 'stats'
      });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['category-breakdown'] });
      
    },
  });
}

// CSV Import mutation
export function useImportCSV() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => transactionService.importCSV(file),
    onSuccess: (result: CSVImportResponse) => {
      // Invalidate all transaction-related queries
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.all });
      // Invalidate ALL stats queries regardless of filters using predicate
      queryClient.invalidateQueries({ 
        predicate: (query) => 
          Array.isArray(query.queryKey) && 
          query.queryKey[0] === 'transactions' && 
          query.queryKey[1] === 'stats'
      });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      queryClient.invalidateQueries({ queryKey: ['category-breakdown'] });
      
      
      // Show success toast
      if (typeof window !== 'undefined') {
        import('sonner').then(({ toast }) => {
          toast.success(`Successfully imported ${result.imported_count} transactions!`);
        });
      }
      
      return result;
    },
    onError: (error) => {
      
      // Provide user-friendly error messages
      let userMessage = 'Import failed. Please check your CSV file and try again.';
      if (error instanceof Error) {
        if (error.message.includes('format')) {
          userMessage = 'Invalid CSV format. Please check the required columns and data types.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          userMessage = 'Network error. Please check your connection and try again.';
        } else if (error.message.includes('validation')) {
          userMessage = 'CSV validation failed. Please check your data format.';
        }
      }
      
      // Show error toast
      if (typeof window !== 'undefined') {
        import('sonner').then(({ toast }) => {
          toast.error(userMessage);
        });
      }
    },
  });
}

// Export transactions mutation
export function useExportTransactions() {
  return useMutation({
    mutationFn: (filters: ExportFilters) => transactionService.exportTransactions(filters),
    onSuccess: async (blob, filters) => {
      try {
        // Download the file
        const filename = `transactions.${filters.format}`;
        transactionService.downloadExportFile(blob, filename);
        
        // Show success feedback to user
        if (typeof window !== 'undefined' && 'navigator' in window && 'vibrate' in navigator) {
          navigator.vibrate?.(200); // Haptic feedback on mobile
        }
        
        // Show success toast
        if (typeof window !== 'undefined') {
          const { toast } = await import('sonner');
          toast.success(`Export completed! File downloaded as ${filename}`);
        }
      } catch (error) {
        throw error; // Re-throw to trigger onError
      }
    },
    onError: (error) => {
      
      // Provide user-friendly error messages
      let userMessage = 'Export failed. Please try again.';
      if (error instanceof Error) {
        if (error.message.includes('empty')) {
          userMessage = 'No data to export with current filters.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          userMessage = 'Network error. Please check your connection and try again.';
        } else if (error.message.includes('download')) {
          userMessage = 'Download failed. Your browser may have blocked the download.';
        }
      }
      
      // Show error toast
      if (typeof window !== 'undefined') {
        import('sonner').then(({ toast }) => {
          toast.error(userMessage);
        });
      }
      logger.error('User message:', userMessage);
    },
  });
}

// Utility hooks that combine multiple operations
export function useTransactionActions() {
  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const deleteMutation = useDeleteTransaction();
  const bulkDeleteMutation = useBulkDeleteTransactions();
  const importMutation = useImportCSV();
  const exportMutation = useExportTransactions();

  return {
    // Basic CRUD
    create: createMutation.mutate,
    update: updateMutation.mutate,
    delete: deleteMutation.mutate,
    bulkDelete: bulkDeleteMutation.mutate,
    
    // Import/Export
    importCSV: importMutation.mutate,
    export: exportMutation.mutate,
    
    // Loading states
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isBulkDeleting: bulkDeleteMutation.isPending,
    isImporting: importMutation.isPending,
    isExporting: exportMutation.isPending,
    
    // Errors
    createError: createMutation.error,
    updateError: updateMutation.error,
    deleteError: deleteMutation.error,
    bulkDeleteError: bulkDeleteMutation.error,
    importError: importMutation.error,
    exportError: exportMutation.error,
    
    // Success data
    importResult: importMutation.data,
  };
}

// Hook for infinite pagination (useful for large transaction lists)
export function useInfiniteTransactions(filters?: Partial<TransactionFilters>) {
  const baseFilters = { per_page: 20, ...filters };
  
  return useQuery({
    queryKey: TRANSACTION_KEYS.list(baseFilters),
    queryFn: () => transactionService.getTransactions(baseFilters),
    staleTime: 2 * 60 * 1000,
  });
}

// Hook for real-time transaction stats (lighter than full transaction list)
export function useTransactionSummary(filters?: TransactionFilter) {
  return useQuery({
    queryKey: TRANSACTION_KEYS.stats(filters),
    queryFn: () => transactionService.getTransactionStats(filters),
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes
  });
}
