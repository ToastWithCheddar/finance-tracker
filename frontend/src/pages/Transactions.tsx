import { useState, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui';
import { ErrorState } from '../components/ui/ErrorState';
import { TransactionList } from '../components/transactions/TransactionList';
import { TransactionFilters } from '../components/transactions/TransactionFilters';
import { TransactionForm } from '../components/transactions/TransactionForm';
import { CSVImport } from '../components/transactions/CSVImport';
import { useTransactions, useTransactionStats, useTransactionActions } from '../hooks/useTransactions';
import { useCategories } from '../hooks/useCategories';
import type { 
  CreateTransactionRequest as TransactionCreate, 
  UpdateTransactionRequest as TransactionUpdate, 
  TransactionFilters as TransactionFilter,
  Transaction
} from '../types/transaction';
import type { TransactionFilters as TransactionFiltersType } from '../services/transactionService';
import { ReceiptText, Brain } from 'lucide-react';
import { mlService } from '../services/mlService';


// Tab definitions
type TransactionTab = 'all';

interface TabConfig {
  id: TransactionTab;
  label: string;
  icon: React.ComponentType<any>;
  description: string;
}



export function Transactions() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Tab configuration
  const tabs: TabConfig[] = [
    {
      id: 'all',
      label: 'All Transactions',
      icon: ReceiptText,
      description: 'Browse, filter, and manage all your transactions'
    }
  ];

  // Get initial tab from URL params or default to 'all'
  const getInitialTab = (): TransactionTab => {
    const tabParam = searchParams.get('tab') as TransactionTab;
    return tabs.find(t => t.id === tabParam)?.id || 'all';
  };

  // Tab state
  const [activeTab, setActiveTab] = useState<TransactionTab>(getInitialTab);

  // Update URL when tab changes
  const handleTabChange = (tab: TransactionTab) => {
    setActiveTab(tab);
    const newParams = new URLSearchParams(searchParams);
    newParams.set('tab', tab);
    setSearchParams(newParams);
  };

  // Sync tab state with URL on mount and URL changes
  useEffect(() => {
    const tabParam = searchParams.get('tab') as TransactionTab;
    const validTab = tabs.find(t => t.id === tabParam)?.id || 'all';
    if (validTab !== activeTab) {
      setActiveTab(validTab);
    }
  }, [searchParams, tabs, activeTab]);
  
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
  const [isBatchCategorizing, setIsBatchCategorizing] = useState(false);
  
  // Refs for click outside handling
  const exportDropdownRef = useRef<HTMLDivElement>(null);

  // Build query parameters for the API
  const queryFilters: Partial<TransactionFiltersType> = {
    ...filters,
    page: currentPage,
    per_page: itemsPerPage,
  };
  

  // Always fetch flat transaction data - no more grouping
  const { data: transactionData, isLoading, error } = useTransactions(queryFilters);
  const { data: stats } = useTransactionStats(filters);
  
  // Fetch categories for filters
  const { data: categories = [], isLoading: categoriesLoading } = useCategories();
  
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

  // Extract data from the flat transaction response
  const transactions = transactionData?.items || [];
  const totalCount = transactionData?.total || 0;
  const totalPages = transactionData?.pages || 1;
  
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

  const handleBatchCategorize = async () => {
    if (!transactions.length) return;
    
    // Find uncategorized transactions (those without categoryId)
    const uncategorizedTransactions = transactions.filter(t => !t.categoryId);
    
    if (uncategorizedTransactions.length === 0) {
      alert('All visible transactions are already categorized!');
      return;
    }

    const confirmed = confirm(`This will automatically categorize ${uncategorizedTransactions.length} uncategorized transactions using AI. Continue?`);
    if (!confirmed) return;

    try {
      setIsBatchCategorizing(true);
      
      // Process in chunks to avoid overwhelming the system
      const CHUNK_SIZE = 50;
      const chunks = [];
      for (let i = 0; i < uncategorizedTransactions.length; i += CHUNK_SIZE) {
        chunks.push(uncategorizedTransactions.slice(i, i + CHUNK_SIZE));
      }

      let totalCategorized = 0;
      const updatedTransactionIds: string[] = []; // Track for potential rollback

      // Process each chunk sequentially
      for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
        const chunk = chunks[chunkIndex];
        
        try {
          // Prepare batch request for this chunk
          const batchRequest = {
            transactions: chunk.map(t => ({
              id: t.id,
              description: t.description,
              amount: t.amountCents
            }))
          };

          // Call ML service for batch categorization
          const result = await mlService.batchCategorizeTransactions(batchRequest);
          
          // Update transactions with high confidence suggestions
          const predictions = result.results ?? [];
          for (let i = 0; i < predictions.length; i++) {
            const pred = predictions[i];
            const confidence = pred.prediction?.confidence ?? 0;
            const suggestedCategoryId = pred.prediction?.categoryId;
            if (suggestedCategoryId && confidence >= 0.7) { // Only auto-apply high confidence
              try {
                const originalTransaction = chunk[i];
                await update({
                  transactionId: originalTransaction.id,
                  transaction: { id: originalTransaction.id, categoryId: suggestedCategoryId }
                });
                
                // Track successful updates for potential rollback
                updatedTransactionIds.push(originalTransaction.id);
                totalCategorized++;
              } catch (error) {
                console.error(`Failed to update transaction ${chunk[i].id}:`, error);
                // Continue with next transaction rather than failing entire batch
              }
            }
          }

          // Show progress for large batches
          if (chunks.length > 1) {
            console.log(`Processed chunk ${chunkIndex + 1}/${chunks.length} (${totalCategorized} categorized so far)`);
          }

        } catch (chunkError) {
          console.error(`Failed to process chunk ${chunkIndex + 1}:`, chunkError);
          // Continue with next chunk rather than failing entire batch
          if (chunks.length > 1) {
            console.log(`Skipping failed chunk ${chunkIndex + 1}, continuing with remaining chunks`);
          }
        }
      }
      
      // Store rollback info in session storage for "undo" functionality
      if (updatedTransactionIds.length > 0) {
        sessionStorage.setItem('lastBatchUpdate', JSON.stringify({
          timestamp: Date.now(),
          updatedTransactionIds,
          totalCount: updatedTransactionIds.length
        }));
      }
      
      alert(`Successfully auto-categorized ${totalCategorized} transactions!${updatedTransactionIds.length > 0 ? '\n\nNote: You can undo this batch operation if needed.' : ''}`);
      
    } catch (error) {
      console.error('Batch categorization failed:', error);
      alert('Batch categorization failed. Please try again.');
    } finally {
      setIsBatchCategorizing(false);
    }
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
  const isBusy = isLoading || isCreating || isUpdating || isDeleting || isBulkDeleting || isImporting || isExporting || categoriesLoading;

  // Error handling
  if (error) {
    return (
      <div className="min-h-screen">
        <ErrorState
          error={error}
          message="Failed to load transactions"
          onRetry={() => window.location.reload()}
          retryLabel="Retry"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'hsl(var(--bg))' }}>
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 glass-surface p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold">Transactions</h1>
              <p className="text-[hsl(var(--text))/0.7] mt-2">Browse, filter, and manage all your transactions</p>
            </div>
            
            {/* Tab-specific action buttons */}
            {activeTab === 'all' && (
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
                    {isExporting ? (
                      <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                        Exporting...
                      </div>
                    ) : (
                      <>
                        Export
                        <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </>
                    )}
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
                
                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      setEditingTransaction(undefined);
                      setIsFormOpen(true);
                    }}
                    className="bg-brand hover:brightness-110"
                  >
                    Add Transaction
                  </Button>
                  
                  <Button
                    onClick={handleBatchCategorize}
                    disabled={isBatchCategorizing || transactions.filter(t => !t.categoryId).length === 0}
                    variant="outline"
                    className="flex items-center gap-2"
                  >
                    <Brain className="h-4 w-4" />
                    {isBatchCategorizing ? 'Categorizing...' : 'Smart Categorize'}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Tab Navigation */}
          <div className="border-t border-[hsl(var(--border))] pt-6">
            <nav className="flex space-x-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`
                      flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                      ${isActive
                        ? 'bg-[hsl(var(--brand))] text-white shadow-md'
                        : 'text-[hsl(var(--text))/0.7] hover:text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)]'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'all' && (
          <>
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
          </>
        )}

        

        {/* Pagination - Only for All Transactions tab */}
        {activeTab === 'all' && !isLoading && totalPages > 1 && (
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
                const endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
                
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

        {/* Modals - Only for All Transactions tab */}
        {activeTab === 'all' && (
          <>
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
              isLoading={isImporting}
            />
          </>
        )}
      </div>
    </div>
  );
}
