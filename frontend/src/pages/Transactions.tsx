import { useState, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
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
  TransactionFilters as TransactionFilter,
  Transaction
} from '../types/transaction';
import type { TransactionFilters as TransactionFiltersType } from '../services/transactionService';

// Define the shape of our grouped data
interface GroupedTransactions {
  [date: string]: {
    transactions: Transaction[];
    total: number; // Net total in cents for the day
  };
}



export function Transactions() {
  const [searchParams] = useSearchParams();
  
  // Get initial filters from URL params
  const getInitialFilters = (): TransactionFilter => {
    const urlFilters: TransactionFilter = {};
    
    if (searchParams.get('dateFrom')) {
      urlFilters.dateFrom = searchParams.get('dateFrom')!;
    }
    if (searchParams.get('dateTo')) {
      urlFilters.dateTo = searchParams.get('dateTo')!;
    }
    if (searchParams.get('categoryId')) {
      urlFilters.categoryId = searchParams.get('categoryId')!;
    }
    if (searchParams.get('accountId')) {
      urlFilters.accountId = searchParams.get('accountId')!;
    }
    if (searchParams.get('merchant')) {
      urlFilters.merchant = searchParams.get('merchant')!;
    }
    if (searchParams.get('search')) {
      urlFilters.search = searchParams.get('search')!;
    }
    
    return urlFilters;
  };

  // State for filters and pagination
  const [filters, setFilters] = useState<TransactionFilter>(getInitialFilters);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(25);
  
  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isExportDropdownOpen, setIsExportDropdownOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<any>();
  
  // Date grouping state
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  
  // Refs for click outside handling
  const exportDropdownRef = useRef<HTMLDivElement>(null);

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

  // Extract data from the response - handle both grouped and flat responses
  const isGroupedResponse = (transactionData as any)?.grouped;
  const groups = (transactionData as any)?.groups || [];
  const transactions = transactionData?.items || [];
  const totalCount = transactionData?.total || 0;
  const totalPages = transactionData?.pages || 1;
  
  // Debug logging for data structure issues
  console.log('🔍 Transaction data structure:', {
    hasData: !!transactionData,
    isGrouped: isGroupedResponse,
    groupsCount: groups.length,
    transactionsCount: transactions.length,
    sampleTransaction: transactions[0]
  });
  
  // Group transactions by date using useMemo for performance (legacy fallback)
  const groupedTransactions = useMemo(() => {
    if (isGroupedResponse) return {}; // Don't group if already grouped by server
    
    // Add defensive programming to prevent crashes
    if (!Array.isArray(transactions) || transactions.length === 0) {
      console.warn('⚠️ No transactions to group or transactions is not an array');
      return {};
    }
    
    return transactions.reduce((acc: GroupedTransactions, tx) => {
      // Defensive check for transaction date - handle both camelCase and snake_case
      const transactionDate = tx.transactionDate || tx.transaction_date;
      if (!tx || !transactionDate) {
        console.warn('⚠️ Transaction missing transactionDate/transaction_date:', tx);
        return acc; // Skip this transaction
      }
      
      // Convert date to string if it's not already (backend might send Date object)
      const dateStr = typeof transactionDate === 'string' 
        ? transactionDate 
        : transactionDate.toString();
      
      // Handle both full datetime strings and date-only strings
      const date = dateStr.includes('T') ? dateStr.split('T')[0] : dateStr;
      
      if (!acc[date]) {
        acc[date] = { transactions: [], total: 0 };
      }
      acc[date].transactions.push(tx);
      acc[date].total += (tx.amountCents || tx.amount_cents || 0);
      return acc;
    }, {});
  }, [transactions, isGroupedResponse]);
  
  // Determine grouping type from filters
  const groupType = filters.group_by || 'date';
  
  // Toggle group expansion
  const toggleGroup = (date: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(date)) {
        newSet.delete(date);
      } else {
        newSet.add(date);
      }
      return newSet;
    });
  };
  
  // Initialize with the most recent date expanded
  useEffect(() => {
    const dates = Object.keys(groupedTransactions).sort((a, b) => b.localeCompare(a));
    if (dates.length > 0) {
      setExpandedGroups(new Set([dates[0]]));
    }
  }, [groupedTransactions]);

  // Handle click outside for export dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (exportDropdownRef.current && !exportDropdownRef.current.contains(event.target as Node)) {
        setIsExportDropdownOpen(false);
      }
    }

    if (isExportDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isExportDropdownOpen]);

  // Get unique categories for filter dropdown (from current transactions)
  const categories = Array.from(
    new Set(
      Array.isArray(transactions) 
        ? transactions.map(t => t?.categoryId).filter((c): c is string => !!c)
        : []
    )
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

  const handleDeleteTransaction = (transactionId: string) => {
    deleteTransaction(transactionId);
  };

  const handleBulkDelete = (transactionIds: string[]) => {
    bulkDelete(transactionIds);
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
    // Map frontend filter field names to backend API parameter names
    const exportFilters = {
      format,
      start_date: filters.dateFrom,
      end_date: filters.dateTo,
      category_id: filters.categoryId,
      transaction_type: filters.transaction_type,
    };

    console.log('🎯 Exporting with filters:', exportFilters);
    exportTransactions(exportFilters);
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
    <div className="min-h-screen" style={{ backgroundColor: 'hsl(var(--bg))' }}>
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 glass-surface p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Transactions</h1>
              <p className="text-[hsl(var(--text))/0.7] mt-2">Manage your income and expenses</p>
            </div>
            
            <div className="flex space-x-3">
              <Button
                variant="outline"
                onClick={() => setIsImportOpen(true)}
              >
                Import CSV
              </Button>
              
              <div className="relative" ref={exportDropdownRef}>
                <Button 
                  variant="outline"
                  disabled={isExporting}
                  onClick={() => setIsExportDropdownOpen(!isExportDropdownOpen)}
                  className="flex items-center"
                >
                  {isExporting ? 'Exporting...' : 'Export'}
                  <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </Button>
                
                {isExportDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-[hsl(var(--surface))] border border-[hsl(var(--border))] z-10">
                    <div className="py-1">
                      <button
                        onClick={() => {
                          handleExport('csv');
                          setIsExportDropdownOpen(false);
                        }}
                        disabled={isExporting}
                        className="flex items-center w-full px-4 py-2 text-sm text-left text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] disabled:opacity-50"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Export as CSV
                      </button>
                      <button
                        onClick={() => {
                          handleExport('json');
                          setIsExportDropdownOpen(false);
                        }}
                        disabled={isExporting}
                        className="flex items-center w-full px-4 py-2 text-sm text-left text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] disabled:opacity-50"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Export as JSON
                      </button>
                    </div>
                  </div>
                )}
              </div>
              
              <Button
                onClick={() => {
                  setEditingTransaction(undefined);
                  setIsFormOpen(true);
                }}
                className="bg-brand hover:brightness-110"
              >
                Add Transaction
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
              groupedTransactions={isGroupedResponse ? undefined : groupedTransactions}
              groups={isGroupedResponse ? groups : undefined}
              expandedGroups={expandedGroups}
              onToggleGroup={toggleGroup}
              stats={stats}
              isLoading={isBusy}
              onEdit={handleEditTransaction}
              onDelete={handleDeleteTransaction}
              onBulkDelete={handleBulkDelete}
              groupType={groupType as 'date' | 'category' | 'merchant' | 'none'}
            />
          </div>
        )}

        {/* Pagination */}
        {!isLoading && totalPages > 1 && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-[hsl(var(--text))/0.75]">
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
              
              {(() => {
                // Calculate the range of pages to show (sliding window)
                const maxPagesToShow = 5;
                let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
                let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
                
                // Adjust if we're near the end
                if (endPage - startPage + 1 < maxPagesToShow) {
                  startPage = Math.max(1, endPage - maxPagesToShow + 1);
                }
                
                return Array.from({ length: endPage - startPage + 1 }, (_, i) => {
                  const page = startPage + i;
                  return (
                    <Button
                      key={page}
                      variant={currentPage === page ? "primary" : "outline"}
                      onClick={() => setCurrentPage(page)}
                    >
                      {page}
                    </Button>
                  );
                });
              })()}
              
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