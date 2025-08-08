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
const TRANSACTION_KEYS = {
  all: ['transactions'] as const,
  lists: () => [...TRANSACTION_KEYS.all, 'list'] as const,
  list: (filters?: Partial<TransactionFilters>) => [...TRANSACTION_KEYS.lists(), filters] as const,
  details: () => [...TRANSACTION_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...TRANSACTION_KEYS.details(), id] as const,
  stats: (filters?: TransactionFilter) => [...TRANSACTION_KEYS.all, 'stats', filters] as const,
} as const;

// Get transactions with filters and pagination
export function useTransactions(filters?: Partial<TransactionFilters>) {
  return useQuery({
    queryKey: TRANSACTION_KEYS.list(filters),
    queryFn: () => transactionService.getTransactions(filters),
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
      
      // Also invalidate budget-related queries since transactions affect budgets
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      
      // Invalidate dashboard data
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.stats() });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.stats() });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      queryClient.invalidateQueries({ queryKey: TRANSACTION_KEYS.stats() });
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      
      return result;
    },
  });
}

// Export transactions mutation
export function useExportTransactions() {
  return useMutation({
    mutationFn: (filters: ExportFilters) => transactionService.exportTransactions(filters),
    onSuccess: (blob, filters) => {
      // Download the file
      const filename = `transactions.${filters.format}`;
      transactionService.downloadExportFile(blob, filename);
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