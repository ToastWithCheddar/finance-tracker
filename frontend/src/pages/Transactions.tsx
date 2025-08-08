import { useState } from 'react';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui';
import { TransactionList } from '../components/transactions/TransactionList';
import { TransactionFilters } from '../components/transactions/TransactionFilters';
import { TransactionForm } from '../components/transactions/TransactionForm';
import { CSVImport } from '../components/transactions/CSVImport';
import { useTransactions, useTransactionStats, useTransactionActions } from '../hooks/useTransactions';
import type { 
  CreateTransactionRequest as TransactionCreate, 
  UpdateTransactionRequest as TransactionUpdate, 
  TransactionFilters as TransactionFilter
} from '../types/transaction';
import type { TransactionFilters as TransactionFiltersType } from '../services/transactionService';



export function Transactions() {
  // State for filters and pagination
  const [filters, setFilters] = useState<TransactionFilter>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(25);
  
  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<any>();

  // Build query parameters for the API
  const queryFilters: Partial<TransactionFiltersType> = {
    ...filters,
    page: currentPage,
    per_page: itemsPerPage,
  };

  // Data fetching with React Query
  const { data: transactionData, isLoading, error } = useTransactions(queryFilters);
  const { data: stats } = useTransactionStats(filters);
  
  // Mutations
  const { 
    create, 
    update, 
    delete: deleteTransaction, 
    bulkDelete, 
    importCSV, 
    export: exportTransactions,
    isCreating, 
    isUpdating, 
    isDeleting, 
    isBulkDeleting, 
    isImporting, 
    isExporting 
  } = useTransactionActions();

  // Extract data from the response
  const transactions = transactionData?.items || [];
  const totalCount = transactionData?.total || 0;
  const totalPages = transactionData?.pages || 1;

  // Get unique categories for filter dropdown (from current transactions)
  const categories = Array.from(
    new Set(transactions.map(t => t.categoryId).filter((c): c is string => !!c))
  ).sort();

  // Handle filter changes (triggers new API call)
  const handleFiltersChange = (newFilters: TransactionFilter) => {
    setFilters(newFilters);
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handleCreateTransaction = (data: TransactionCreate) => {
    create(data, {
      onSuccess: () => {
        setIsFormOpen(false);
      },
    });
  };

  const handleUpdateTransaction = (data: TransactionUpdate) => {
    if (!editingTransaction) return;
    
    update({ transactionId: editingTransaction.id.toString(), transaction: data }, {
      onSuccess: () => {
        setIsFormOpen(false);
        setEditingTransaction(undefined);
      },
    });
  };

  const handleDeleteTransaction = (transactionId: number) => {
    deleteTransaction(transactionId.toString());
  };

  const handleBulkDelete = (transactionIds: number[]) => {
    bulkDelete(transactionIds.map(id => id.toString()));
  };

  const handleEditTransaction = (transaction: any) => {
    setEditingTransaction(transaction);
    setIsFormOpen(true);
  };

  const handleCSVImport = async (file: File) => {
    importCSV(file, {
      onSuccess: () => {
        setIsImportOpen(false);
      },
    });
  };

  const handleClearFilters = () => {
    setFilters({});
  };

  const handleExport = (format: 'csv' | 'json') => {
    exportTransactions({
      ...filters,
      format,
    });
  };

  // Common submit handler that delegates to create or update depending on edit state
  const handleTransactionSubmit = async (data: TransactionCreate | TransactionUpdate) => {
    if (editingTransaction) {
      handleUpdateTransaction(data as TransactionUpdate);
    } else {
      handleCreateTransaction(data as TransactionCreate);
    }
  };

  // Loading state for any operation
  const isBusy = isLoading || isCreating || isUpdating || isDeleting || isBulkDeleting || isImporting || isExporting;

  // Error handling
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load transactions</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Transactions</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">Manage your income and expenses</p>
            </div>
            
            <div className="flex space-x-3">
              <Button
                variant="outline"
                onClick={() => setIsImportOpen(true)}
              >
                📥 Import CSV
              </Button>
              
              <div className="relative group">
                <Button variant="outline">
                  📤 Export
                </Button>
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                  <div className="py-1">
                    <button
                      onClick={() => handleExport('csv')}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleExport('json')}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Export as JSON
                    </button>
                  </div>
                </div>
              </div>
              
              <Button
                onClick={() => {
                  setEditingTransaction(undefined);
                  setIsFormOpen(true);
                }}
                className="bg-blue-600 hover:bg-blue-700"
              >
                ➕ Add Transaction
              </Button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6">
          <TransactionFilters
            filters={filters}
            onFiltersChange={handleFiltersChange}
            onClearFilters={handleClearFilters}
            categories={categories}
          />
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {/* Transaction List */}
        {!isLoading && (
          <div className="mb-8">
            <TransactionList
              transactions={transactions}
              stats={stats}
              isLoading={isBusy}
              onEdit={handleEditTransaction}
              onDelete={handleDeleteTransaction}
              onBulkDelete={handleBulkDelete}
            />
          </div>
        )}

        {/* Pagination */}
        {!isLoading && totalPages > 1 && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
              {Math.min(currentPage * itemsPerPage, totalCount)} of{' '}
              {totalCount} transactions
            </div>
            
            <div className="flex space-x-2">
              <Button
                variant="outline"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const page = i + 1;
                return (
                  <Button
                    key={page}
                    variant={currentPage === page ? "primary" : "outline"}
                    onClick={() => setCurrentPage(page)}
                  >
                    {page}
                  </Button>
                );
              })}
              
              <Button
                variant="outline"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}

        {/* Modals */}
        <TransactionForm
          isOpen={isFormOpen}
          onClose={() => {
            setIsFormOpen(false);
            setEditingTransaction(undefined);
          }}
          onSubmit={handleTransactionSubmit}
          transaction={editingTransaction}
          title={editingTransaction ? 'Edit Transaction' : 'Add Transaction'}
          // isLoading={isCreating || isUpdating}
        />

        <CSVImport
          isOpen={isImportOpen}
          onClose={() => setIsImportOpen(false)}
          onImport={handleCSVImport}
          // isLoading={isImporting}
        />
      </div>
    </div>
  );
}