import { BaseService } from './base/BaseService';
import { apiClient } from './api';
import type { 
  Transaction, 
  CreateTransactionRequest, 
  UpdateTransactionRequest, 
  TransactionFilters,
  TransactionSummary,
  TransactionStats
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
      accountName: transaction.account_name || transaction.accountName || 'Unknown Account',
      accountType: transaction.account_type || transaction.accountType,
      categoryId: transaction.category_id || transaction.categoryId,
      categoryName: transaction.category_name || transaction.categoryName,
      amountCents: transaction.amount_cents || transaction.amountCents || 0,
      currency: transaction.currency || 'USD',
      description: transaction.description || '',
      merchant: transaction.merchant,
      // Handle transaction date - convert Date objects to ISO string format
      transactionDate: (() => {
        const date = transaction.transaction_date || transaction.transactionDate;
        if (!date) return '';
        if (typeof date === 'string') return date;
        if (date instanceof Date) return date.toISOString();
        // Handle case where backend returns date as object
        return date.toString();
      })(),
      isRecurring: transaction.is_recurring || transaction.isRecurring || false,
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
    
    // Pagination params
    if (filters?.page) params.page = filters.page;
    if (filters?.per_page) params.per_page = filters.per_page;
    
    // Filter params - map from new TransactionFilters to API parameters
    if (filters?.dateFrom) params.start_date = filters.dateFrom;
    if (filters?.dateTo) params.end_date = filters.dateTo;
    if (filters?.categoryId) params.category_id = filters.categoryId;
    if (filters?.merchant) params.merchant = filters.merchant;
    if (filters?.amountMinCents !== undefined) params.min_amount = filters.amountMinCents;
    if (filters?.amountMaxCents !== undefined) params.max_amount = filters.amountMaxCents;
    if (filters?.search) params.search_query = filters.search;

    console.log('🎯 TransactionService fetching from endpoint:', this.baseEndpoint);
    console.log('📦 With params:', params);
    
    const response = await this.get<any>(
      '/',
      params,
      {
        useCache: options?.useCache ?? true,
        cacheTtl: 2 * 60 * 1000, // 2 minutes cache for transactions
        context: options?.context
      }
    );
    
    console.log('📤 TransactionService raw response:', response);

    // Normalize the response structure and transaction field names
    const normalizedResponse: TransactionListResponse = {
      items: (response.items || []).map((transaction: any) => this.normalizeTransaction(transaction)),
      total: response.total || 0,
      page: response.page || 1,
      per_page: response.per_page || 25,
      pages: response.pages || 1
    };
    
    console.log('✨ TransactionService normalized response:', normalizedResponse);
    return normalizedResponse;
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
    options?: { context?: ErrorContext }
  ): Promise<Transaction> {
    return this.post<Transaction>(
      '/',
      transaction,
      { context: options?.context }
    );
  }

  async updateTransaction(
    transactionId: string,
    transaction: UpdateTransactionRequest,
    options?: { context?: ErrorContext }
  ): Promise<Transaction> {
    return this.put<Transaction>(
      `/${transactionId}`,
      transaction,
      { context: options?.context }
    );
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

  // Helper method to normalize stats response from backend to frontend format
  private normalizeTransactionStats(backendStats: any): TransactionStats {
    // Handle case where backend returns TransactionSummary format (camelCase)
    if (backendStats.totalIncome !== undefined) {
      return {
        total_income: backendStats.totalIncome || 0,
        total_expenses: backendStats.totalExpenses || 0,
        net_amount: backendStats.netAmount || 0,
        transaction_count: backendStats.transactionCount || 0,
        total_count: backendStats.transactionCount || 0, // alias for backward compatibility
        // Calculate missing fields
        average_transaction: backendStats.transactionCount > 0 
          ? Math.abs(backendStats.netAmount) / backendStats.transactionCount 
          : 0,
        transaction_count_by_type: {
          income: Math.round((backendStats.totalIncome / (backendStats.totalIncome + backendStats.totalExpenses || 1)) * (backendStats.transactionCount || 0)),
          expense: Math.round((backendStats.totalExpenses / (backendStats.totalIncome + backendStats.totalExpenses || 1)) * (backendStats.transactionCount || 0))
        }
      };
    }
    
    // Handle case where backend already returns snake_case format
    return {
      total_income: backendStats.total_income || 0,
      total_expenses: backendStats.total_expenses || 0,
      net_amount: backendStats.net_amount || 0,
      transaction_count: backendStats.transaction_count || backendStats.total_count || 0,
      total_count: backendStats.total_count || backendStats.transaction_count || 0,
      average_transaction: backendStats.average_transaction || 0,
      transaction_count_by_type: backendStats.transaction_count_by_type || {
        income: 0,
        expense: 0
      }
    };
  }

  async getTransactionStats(
    filters?: TransactionFilters,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<TransactionStats> {
    const params: Record<string, string | number | boolean> = {};
    
    if (filters?.dateFrom) params.start_date = filters.dateFrom;
    if (filters?.dateTo) params.end_date = filters.dateTo;
    if (filters?.categoryId) params.category_id = filters.categoryId;
    if (filters?.search) params.search_query = filters.search;

    console.log('🎯 TransactionService fetching stats from endpoint:', '/analytics/stats');
    console.log('📦 With params:', params);

    const response = await this.get<any>(
      '/analytics/stats',
      params,
      {
        useCache: options?.useCache ?? true,
        cacheTtl: 5 * 60 * 1000, // 5 minutes cache for stats
        context: options?.context
      }
    );
    
    console.log('📤 TransactionService raw stats response:', response);

    // Normalize the response to match frontend expectations
    const normalizedStats = this.normalizeTransactionStats(response);
    
    console.log('✨ TransactionService normalized stats:', normalizedStats);
    return normalizedStats;
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
    if (filters.category_id) params.category = filters.category_id; // Backend expects 'category' not 'category_id'
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

  // Merchant recognition methods
  async enrichTransactionWithMerchant(
    transactionId: string,
    description?: string,
    options?: { context?: ErrorContext }
  ): Promise<{
    transaction_id: string;
    original_description: string;
    recognized_merchant: string | null;
    confidence_score: number;
    method_used: string;
    updated: boolean;
  }> {
    const payload: any = {};
    if (description) {
      payload.description = description;
    }

    return this.post<{
      transaction_id: string;
      original_description: string;
      recognized_merchant: string | null;
      confidence_score: number;
      method_used: string;
      updated: boolean;
    }>(
      `/merchants/transactions/${transactionId}/enrich`,
      payload,
      { context: options?.context }
    );
  }

  async correctTransactionMerchant(
    transactionId: string,
    merchantName: string,
    options?: { context?: ErrorContext }
  ): Promise<{
    message: string;
    transaction_id: string;
    corrected_merchant: string;
    learning_updated: boolean;
  }> {
    return this.put<{
      message: string;
      transaction_id: string;
      corrected_merchant: string;
      learning_updated: boolean;
    }>(
      `/merchants/transactions/${transactionId}/correct`,
      { merchant_name: merchantName },
      { context: options?.context }
    );
  }

  async recognizeMerchantFromDescription(
    description: string,
    options?: { context?: ErrorContext }
  ): Promise<{
    original_description: string;
    recognized_merchant: string | null;
    confidence_score: number;
    method_used: string;
    suggestions: string[];
  }> {
    const params = { description };
    
    return this.get<{
      original_description: string;
      recognized_merchant: string | null;
      confidence_score: number;
      method_used: string;
      suggestions: string[];
    }>(
      `/merchants/recognize`,
      params,
      { context: options?.context }
    );
  }

  async getMerchantSuggestions(
    query: string,
    limit: number = 5,
    options?: { context?: ErrorContext }
  ): Promise<{ suggestions: string[] }> {
    const params = { query, limit };
    
    return this.get<{ suggestions: string[] }>(
      `/merchants/suggestions`,
      params,
      { context: options?.context }
    );
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
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        console.log('✅ Download completed and cleaned up');
      }, 100);
    } catch (error) {
      console.error('❌ Download failed:', error);
      throw new Error('Failed to download file');
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

  async getSpendingTrends(period: 'week' | 'month' | 'year' = 'month'): Promise<any[]> {
    const params = { period };
    return this.get<any[]>(
      '/analytics/trends',
      params
    );
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

  async getSpendingTrendsWithWrapper(period: 'week' | 'month' | 'year' = 'month'): Promise<{ success: boolean; data: any[] }> {
    try {
      const data = await this.getSpendingTrends(period);
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