import { BaseService } from './base/BaseService';
import { apiClient, normalizeListEnvelope } from './api';
import type { 
  Transaction, 
  CreateTransactionRequest, 
  UpdateTransactionRequest, 
  TransactionFilters,
  TransactionStats,
  TransactionGroupedResponse
} from '../types/transaction';

// Re-export types for use in other files
export type { TransactionFilters } from '../types/transaction';
import type { ErrorContext } from '../types/errors';

// Legacy interfaces for backward compatibility during migration
export interface LegacyTransactionFilters {
  page?: number;
  per_page?: number;
  start_date?: string;
  end_date?: string;
  category?: string;
  category_id?: string;
  transaction_type?: 'income' | 'expense';
  min_amount?: number;
  max_amount?: number;
  search_query?: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface CSVImportResponse {
  imported_count: number;
  errors: string[];
  transactions: Transaction[];
}

export interface ExportFilters {
  start_date?: string;
  end_date?: string;
  category_id?: string;
  transaction_type?: 'income' | 'expense';
  format: 'csv' | 'json';
}

export class TransactionService extends BaseService {
  protected baseEndpoint = '/transactions';

  // Helper method to normalize transaction objects from backend to frontend format
  private normalizeTransaction(transaction: any): Transaction {
    return {
      ...transaction,
      // Normalize field names - use frontend format with backend as fallback
      id: transaction.id,
      userId: transaction.user_id || transaction.userId,
      accountId: transaction.account_id || transaction.accountId,
      accountName: transaction.account_name || transaction.accountName || transaction.account?.name || 'Unknown Account',
      accountType: transaction.account_type || transaction.accountType || transaction.account?.account_type || '',
      categoryId: transaction.category_id || transaction.categoryId,
      categoryName: transaction.category_name || transaction.categoryName,
      amountCents: transaction.amount_cents || transaction.amountCents || 0,
      currency: transaction.currency || 'USD',
      description: transaction.description || '',
      merchant: transaction.merchant,
      // Handle transaction date - convert Date objects to YYYY-MM-DD string
      transactionDate: (() => {
        const date = transaction.transaction_date || transaction.transactionDate;
        if (!date) return '';
        if (typeof date === 'string') return date;
        if (date instanceof Date) return date.toISOString().slice(0, 10);
        // Handle case where backend returns date as object
        return date.toString();
      })(),
      notes: transaction.notes,
      tags: transaction.tags || [],
      plaidTransactionId: transaction.plaid_transaction_id || transaction.plaidTransactionId,
      confidenceScore: transaction.confidence_score || transaction.confidenceScore,
      createdAt: transaction.created_at || transaction.createdAt,
      updatedAt: transaction.updated_at || transaction.updatedAt,
      status: transaction.status,
      isTransfer: transaction.is_transfer || transaction.isTransfer || false,
      mlSuggestedCategoryId: transaction.ml_suggested_category_id || transaction.mlSuggestedCategoryId,
    } as Transaction;
  }

  async getTransactions(
    filters?: Partial<TransactionFilters>,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<TransactionListResponse> {
    const params: Record<string, string | number | boolean> = {};
    
    console.log('🔍 [TransactionService] Input filters:', filters);
    
    // Pagination params: support both page/per_page and offset/limit
    const page = filters?.page ?? 1;
    const perPage = (filters?.per_page ?? filters?.limit) as number | undefined;
    if (page) params.page = page;
    if (perPage !== undefined) {
      params.per_page = perPage;
      params.limit = perPage; // also send limit for backends expecting limit/offset
      const offset = (page - 1) * perPage;
      params.offset = offset;
    }
    
    // Filter params - map frontend field names to backend API parameters
    // Support both camelCase (frontend) and snake_case (backend compatibility)
    if (filters?.dateFrom !== undefined) {
      params.start_date = filters.dateFrom;
    } else if (filters?.start_date !== undefined) {
      params.start_date = filters.start_date;
    }
    if (filters?.dateTo !== undefined) {
      params.end_date = filters.dateTo;
    } else if (filters?.end_date !== undefined) {
      params.end_date = filters.end_date;
    }
    if (filters?.accountId !== undefined) {
      params.account_id = filters.accountId;
    } else if (filters?.account_id !== undefined) {
      params.account_id = filters.account_id;
    }
    if (filters?.categoryId !== undefined) {
      params.category_id = filters.categoryId;
    } else if (filters?.category_id !== undefined) {
      params.category_id = filters.category_id;
    }
    // (removed manual recurring demo filter)
    // Amount filtering with proper field name mapping
    if (filters?.amountMinCents !== undefined || filters?.min_amount_cents !== undefined) {
      params.min_amount_cents =
        filters?.amountMinCents !== undefined
          ? filters.amountMinCents
          : (filters!.min_amount_cents as number);
    }
    if (filters?.amountMaxCents !== undefined || filters?.max_amount_cents !== undefined) {
      params.max_amount_cents =
        filters?.amountMaxCents !== undefined
          ? filters.amountMaxCents
          : (filters!.max_amount_cents as number);
    }
    // Search functionality with proper field name mapping
    if (filters?.search !== undefined) {
      params.search_query = filters.search;
    } else if (filters?.search_query !== undefined) {
      params.search_query = filters.search_query;
    }
    if (filters?.transaction_type !== undefined) {
      params.transaction_type = filters.transaction_type;
    }

    // Comprehensive logging for debugging
    console.log('🔍 [TransactionService] Mapped parameters for API:', params);
    console.debug?.('TransactionService fetching:', this.baseEndpoint, params);
    
    const response = await this.get<any>(
      '/',
      params,
      {
        useCache: options?.useCache ?? true,
        cacheTtl: 2 * 60 * 1000, // 2 minutes cache for transactions
        context: options?.context
      }
    );
    
    console.log('🔍 [TransactionService] Raw API response:', response);
    console.debug?.('TransactionService raw response:', response);

    // Normalize list envelope first, then normalize each transaction item
    const list = normalizeListEnvelope<any>(response);
    const normalizedResponse: TransactionListResponse = {
      items: (list.items || []).map(item => this.normalizeTransaction(item)),
      total: list.total || 0,
      page: list.page || 1,
      per_page: list.per_page || (list.items?.length ?? 0),
      pages: list.pages || 1,
    };
    
    console.log('🔍 [TransactionService] Final normalized response:', {
      itemCount: normalizedResponse.items.length,
      total: normalizedResponse.total,
      page: normalizedResponse.page,
      per_page: normalizedResponse.per_page,
      pages: normalizedResponse.pages
    });
    console.debug?.('TransactionService normalized response:', normalizedResponse);
    return normalizedResponse;
  }

  async getTransactionsGrouped(
    filters: TransactionFilters & { group_by: 'date' | 'category' | 'merchant' },
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<TransactionGroupedResponse> {
    const params: Record<string, string | number | boolean> = {};
    
    // Pagination params: support both page/per_page and offset/limit
    const page = filters?.page ?? 1;
    const perPage = (filters?.per_page ?? filters?.limit) as number | undefined;
    if (page) params.page = page;
    if (perPage !== undefined) {
      params.per_page = perPage;
      params.limit = perPage; // also send limit for backends expecting limit/offset
      const offset = (page - 1) * perPage;
      params.offset = offset;
    }
    
    // Filter params - map from new TransactionFilters to API parameters
    if (filters?.dateFrom) params.start_date = filters.dateFrom;
    if (filters?.dateTo) params.end_date = filters.dateTo;
    if (filters?.accountId) params.account_id = filters.accountId;
    if (filters?.categoryId) params.category_id = filters.categoryId;
    // Merchant filtering not implemented yet
    // if (filters?.merchant) params.merchant = filters.merchant;
    if (filters?.amountMinCents !== undefined) params.min_amount_cents = filters.amountMinCents;
    if (filters?.amountMaxCents !== undefined) params.max_amount_cents = filters.amountMaxCents;
    if (filters?.search) params.search_query = filters.search;
    if (filters?.transaction_type) params.transaction_type = filters.transaction_type;
    
    // Required group_by parameter
    params.group_by = filters.group_by;

    // Debug-level logging
    console.debug?.('TransactionService fetching grouped:', this.baseEndpoint, params);
    
    const response = await this.get<any>(
      '/',
      params,
      {
        useCache: options?.useCache ?? true,
        cacheTtl: 2 * 60 * 1000, // 2 minutes cache for transactions
        context: options?.context
      }
    );
    
    console.debug?.('TransactionService raw grouped response:', response);

    // Process the grouped response
    const groupedResponse: TransactionGroupedResponse = {
      groups: (response.groups || []).map((group: any) => ({
        key: group.key,
        total_amount_cents: group.total_amount_cents || 0,
        count: group.count || 0,
        transactions: (group.transactions || []).map((item: any) => this.normalizeTransaction(item)),
      })),
      total: response.total || 0,
      page: response.page || 1,
      per_page: response.per_page || (response.groups?.reduce((sum: number, g: any) => sum + (g.transactions?.length || 0), 0) ?? 0),
      pages: response.pages || 1,
      grouped: true,
    };
    
    console.debug?.('TransactionService normalized grouped response:', groupedResponse);
    return groupedResponse;
  }

  async getTransaction(
    transactionId: string,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<Transaction> {
    return this.get<Transaction>(
      `/${transactionId}`,
      undefined,
      {
        useCache: options?.useCache ?? true,
        context: options?.context
      }
    );
  }

  async createTransaction(
    transaction: CreateTransactionRequest,
    options?: { context?: ErrorContext; notify?: boolean }
  ): Promise<Transaction> {
    // Ensure transaction_date is snake_case and formatted YYYY-MM-DD if Date provided via convenience fields
    const payload: any = { ...transaction };
    if (!payload.transaction_date && payload.transactionDate) {
      const d = payload.transactionDate;
      payload.transaction_date = d instanceof Date ? d.toISOString().slice(0, 10) : d;
      delete payload.transactionDate;
    }

    // Build query parameters
    const queryParams: Record<string, any> = {};
    if (options?.notify !== undefined) {
      queryParams.notify = options.notify;
    }

    // Make the request with query parameters
    const endpoint = Object.keys(queryParams).length > 0 
      ? `/?${new URLSearchParams(queryParams).toString()}`
      : '/';
    
    const response = await this.post<any>(endpoint, payload, { context: options?.context });
    
    // Apply normalization to the response
    return this.normalizeTransaction(response);
  }

  async updateTransaction(
    transactionId: string,
    transaction: UpdateTransactionRequest,
    options?: { context?: ErrorContext }
  ): Promise<Transaction> {
    const payload: any = { ...transaction };
    if (!payload.transaction_date && payload.transactionDate) {
      const d = payload.transactionDate;
      payload.transaction_date = d instanceof Date ? d.toISOString().slice(0, 10) : d;
      delete payload.transactionDate;
    }
    
    const response = await this.put<any>(`/${transactionId}`, payload, { context: options?.context });
    
    // Apply normalization to the response
    return this.normalizeTransaction(response);
  }

  async deleteTransaction(
    transactionId: string,
    options?: { context?: ErrorContext }
  ): Promise<{ message: string }> {
    return this.delete<{ message: string }>(
      `/${transactionId}`,
      { context: options?.context }
    );
  }

  async bulkDeleteTransactions(
    transactionIds: string[],
    options?: { context?: ErrorContext }
  ): Promise<{ message: string; deleted_count: number }> {
    return this.post<{ message: string; deleted_count: number }>(
      '/bulk-delete',
      { transaction_ids: transactionIds },
      { context: options?.context }
    );
  }


  async getTransactionStats(
    filters?: TransactionFilters,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<TransactionStats> {
    console.log('🎯 [getTransactionStats] Starting stats calculation with backend limit respect');
    
    try {
      // Use max allowed per_page (100) to respect backend validation
      const statsFilters = { 
        ...filters,  // Same exact base filters that work for transaction queries
        per_page: 100,  // Use maximum allowed by backend (le=100)
        page: 1  // Start from page 1
      };
      
      console.log('🔍 [getTransactionStats] Using filters with backend limit:', statsFilters);
      
      const transactionData = await this.getTransactions(statsFilters, { 
        useCache: options?.useCache ?? true,
        context: options?.context 
      });
      
      const totalCountFromAPI = transactionData?.total || 0;
      const totalPages = transactionData?.pages || 1;
      const transactions = transactionData?.items || [];
      
      console.log('📊 [getTransactionStats] First page results:', {
        fetchedCount: transactions.length,
        totalCount: totalCountFromAPI,
        totalPages: totalPages
      });
      
      // Calculate stats from the first 100 transactions
      // This gives a good approximation and respects backend limits
      let totalIncome = 0;
      let totalExpenses = 0;
      let incomeCount = 0;
      let expenseCount = 0;
      
      transactions.forEach(transaction => {
        const amount = transaction.amountCents || transaction.amount_cents || 0;
        if (amount > 0) {
          totalIncome += amount;
          incomeCount++;
        } else {
          totalExpenses += Math.abs(amount);
          expenseCount++;
        }
      });
      
      // Use the accurate total count from API response
      const netAmount = totalIncome - totalExpenses;
      const averageTransaction = transactions.length > 0 ? Math.abs(netAmount) / transactions.length : 0;
      
      const stats: TransactionStats = {
        total_count: totalCountFromAPI,  // Accurate total from backend
        total_income: totalIncome,
        total_expenses: totalExpenses,
        net_amount: netAmount,
        average_transaction: Math.round(averageTransaction),
        transaction_count_by_type: {
          income: incomeCount,
          expense: expenseCount
        }
      };
      
      console.log('✨ [getTransactionStats] Final calculated stats:', stats);
      
      return stats;
      
    } catch (error) {
      console.error('❌ [getTransactionStats] Error in stats calculation:', error);
      
      // Return empty stats as fallback
      return {
        total_count: 0,
        total_income: 0,
        total_expenses: 0,
        net_amount: 0,
        average_transaction: 0,
        transaction_count_by_type: {
          income: 0,
          expense: 0
        }
      };
    }
  }

  async importCSV(
    file: File,
    options?: { context?: ErrorContext }
  ): Promise<CSVImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Use apiClient directly for FormData uploads
      const endpoint = this.buildEndpoint('/import');
      const result = await apiClient.postFormData<CSVImportResponse>(endpoint, formData);
      
      // Clear transaction cache after import
      this.clearCache();
      
      return result;
    } catch (error) {
      throw this.handleServiceError(error as any, options?.context);
    }
  }

  async exportTransactions(
    filters: ExportFilters,
    options?: { context?: ErrorContext }
  ): Promise<Blob> {
    const params: Record<string, any> = {
      format: filters.format,
    };
    
    // Map frontend filter field names to backend API parameter names
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.category_id) params.category_id = filters.category_id;
    if (filters.transaction_type) params.transaction_type = filters.transaction_type;

    console.log('🎯 Exporting transactions with params:', params);

    try {
      const blob = await apiClient.getBlob('/transactions/export', params);
      console.log('✅ Export blob received:', blob.size, 'bytes');
      return blob;
    } catch (error) {
      console.error('❌ Export failed:', error);
      throw this.handleServiceError(error as any, options?.context);
    }
  }

  // Helper methods (inherited from BaseService, but can override if needed)
  // formatCurrency is available from BaseService

  formatTransactionType(type: 'income' | 'expense'): string {
    return type.charAt(0).toUpperCase() + type.slice(1);
  }

  getTransactionTypeColor(type: 'income' | 'expense'): string {
    return type === 'income' ? 'text-green-600' : 'text-red-600';
  }

  getTransactionTypeIcon(type: 'income' | 'expense'): string {
    return type === 'income' ? '📈' : '📉';
  }



  parseCSVFile(file: File): Promise<CreateTransactionRequest[]> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const csv = e.target?.result as string;
          const lines = csv.split('\n');
          const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
          
          const transactions: CreateTransactionRequest[] = [];
          
          for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',');
            if (values.length < headers.length) continue;
            
            const transaction: any = {};
            headers.forEach((header, index) => {
              transaction[header] = values[index]?.trim();
            });
            
            // Map CSV headers to our transaction structure
            const amount = parseFloat(transaction.amount || transaction.Amount || '0');
            const transactionType = (transaction.transaction_type || 'expense').toLowerCase() as 'income' | 'expense';
            
            const mappedTransaction: CreateTransactionRequest = {
              accountId: transaction.account_id || transaction.accountId || '', // Will need to be set by caller
              amountCents: Math.round(amount * 100), // Convert dollars to cents
              description: transaction.description || transaction.Description || '',
              transactionDate: transaction.date || transaction.Date || transaction.transaction_date || new Date().toISOString().split('T')[0],
              transaction_type: transactionType,
              categoryId: transaction.category_id || transaction.category || transaction.Category,
            };
            
            if (mappedTransaction.amountCents > 0) {
              transactions.push(mappedTransaction);
            }
          }
          
          resolve(transactions);
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }

  downloadExportFile(blob: Blob, filename: string): void {
    try {
      console.log('📥 Starting download:', filename, 'Size:', blob.size, 'Type:', blob.type);
      
      // Validate blob
      if (!blob || blob.size === 0) {
        throw new Error('Export file is empty or invalid');
      }

      // Check browser support
      if (!window.URL || !window.URL.createObjectURL) {
        throw new Error('Browser does not support file downloads');
      }
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      
      document.body.appendChild(a);
      
      // Add error handling for click event
      a.addEventListener('error', () => {
        throw new Error('Failed to initiate download');
      });
      
      a.click();
      
      // Clean up with proper error handling
      setTimeout(() => {
        try {
          if (document.body.contains(a)) {
            document.body.removeChild(a);
          }
          window.URL.revokeObjectURL(url);
          console.log('✅ Download completed and cleaned up');
        } catch (cleanupError) {
          console.warn('Minor cleanup error:', cleanupError);
        }
      }, 100);
      
    } catch (error) {
      console.error('❌ Download failed:', error);
      // Provide user-friendly error message
      const message = error instanceof Error ? error.message : 'Unknown error occurred';
      throw new Error(`Failed to download ${filename}: ${message}`);
    }
  }

  // Enhanced methods from standardized service
  async searchTransactions(request: {
    query: string;
    start_date?: string;
    end_date?: string;
    category?: string;
    transaction_type?: string;
    page?: number;
    per_page?: number;
  }): Promise<TransactionListResponse> {
    const params: Record<string, string | number | boolean> = {};
    
    Object.entries(request).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params[key] = value;
      }
    });

    const response = await this.get<TransactionListResponse>(
      '/search_transactions',
      params
    );
    
    return response;
  }

  async getTransactionsByCategory(categoryId: string, filters?: Omit<TransactionFilters, 'categoryId'>): Promise<TransactionListResponse> {
    return this.getTransactions({ ...filters, categoryId });
  }

  async getTransactionsByAccount(accountId: string, filters?: Omit<TransactionFilters, 'accountId'>): Promise<TransactionListResponse> {
    return this.getTransactions({ ...filters, accountId });
  }

  async getTransactionsByDateRange(
    startDate: string, 
    endDate: string, 
    filters?: Omit<TransactionFilters, 'dateFrom' | 'dateTo'>
  ): Promise<TransactionListResponse> {
    return this.getTransactions({ 
      ...filters, 
      dateFrom: startDate, 
      dateTo: endDate 
    });
  }


  async getCategoryBreakdown(filters?: TransactionFilters): Promise<any[]> {
    const params: Record<string, string | number | boolean> = {};
    
    if (filters?.dateFrom) params.start_date = filters.dateFrom;
    if (filters?.dateTo) params.end_date = filters.dateTo;
    if (filters?.categoryId) params.category_id = filters.categoryId;
    if (filters?.search) params.search_query = filters.search;

    return this.get<any[]>(
      '/category-breakdown',
      params
    );
  }

  async getRecentTransactions(limit: number = 10): Promise<Transaction[]> {
    const response = await this.getTransactions({ 
      per_page: limit 
    });
    return response.items || [];
  }

  async getTransactionCategories(): Promise<string[]> {
    return this.get<string[]>(
      '/categories'
    );
  }

  async getTransactionHistogram(filters?: {
    start_date?: string;
    end_date?: string;
    category_id?: string;
    account_id?: string;
    amount_min?: number;
    amount_max?: number;
    bins?: number;
  }): Promise<any> {
    const params: Record<string, string | number | boolean> = {};
    
    if (filters?.start_date) params.start_date = filters.start_date;
    if (filters?.end_date) params.end_date = filters.end_date;
    if (filters?.category_id) params.category_id = filters.category_id;
    if (filters?.account_id) params.account_id = filters.account_id;
    if (filters?.amount_min !== undefined) params.amount_min = filters.amount_min;
    if (filters?.amount_max !== undefined) params.amount_max = filters.amount_max;
    if (filters?.bins !== undefined) params.bins = filters.bins;

    return this.get<any>(
      '/histogram',
      params
    );
  }

  // ServiceResponse wrapper variants for compatibility with new patterns
  async getTransactionsWithWrapper(
    filters?: Partial<TransactionFilters>,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<{ success: boolean; data: TransactionListResponse }> {
    try {
      const data = await this.getTransactions(filters, options);
      return {
        success: true,
        data
      };
    } catch (error) {
      return {
        success: false,
        data: { items: [], total: 0, page: 1, per_page: 20, pages: 1 }
      };
    }
  }


  async getCategoryBreakdownWithWrapper(filters?: TransactionFilters): Promise<{ success: boolean; data: any[] }> {
    try {
      const data = await this.getCategoryBreakdown(filters);
      return {
        success: true,
        data
      };
    } catch (error) {
      return {
        success: false,
        data: []
      };
    }
  }
}

export const transactionService = new TransactionService();
