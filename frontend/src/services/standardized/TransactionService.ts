/**
 * Standardized Transaction Service using BaseService patterns
 */
import { BaseService, ServiceResponse, BaseFilters } from '../base/BaseService';
import type { 
  Transaction, 
  TransactionCreate, 
  TransactionUpdate, 
  TransactionListResponse,
  TransactionStats
} from '../../types/transactions';
import type { SpendingTrend } from '../dashboardService';

// Transaction-specific filters
export interface TransactionFilters extends BaseFilters {
  start_date?: string;
  end_date?: string;
  category_id?: string;
  category?: string;
  transaction_type?: 'income' | 'expense';
  min_amount?: number;
  max_amount?: number;
  search_query?: string;
  account_id?: string;
  merchant?: string;
  status?: string;
}

// CSV import/export types
export interface CSVImportResponse {
  imported_count: number;
  errors: string[];
  transactions: Transaction[];
  skipped_count?: number;
  duplicate_count?: number;
}

export interface ExportFilters {
  start_date?: string;
  end_date?: string;
  category_id?: string;
  transaction_type?: 'income' | 'expense';
  format: 'csv' | 'json';
}

export interface BulkDeleteRequest {
  transaction_ids: string[];
}

export interface BulkDeleteResponse {
  deleted_count: number;
  failed_count: number;
  errors: string[];
}

export interface TransactionSearchRequest {
  query: string;
  start_date?: string;
  end_date?: string;
  category?: string;
  transaction_type?: string;
  page?: number;
  per_page?: number;
}

export class StandardizedTransactionService extends BaseService {
  protected readonly baseEndpoint = '/transactions';
  
  /**
   * Get transactions with filters and pagination
   */
  async getTransactions(filters?: TransactionFilters): Promise<ServiceResponse<TransactionListResponse>> {
    const params = this.buildParams(filters || {});
    return this.get<TransactionListResponse>(this.baseEndpoint, params);
  }
  
  /**
   * Get a single transaction by ID
   */
  async getTransaction(id: string): Promise<ServiceResponse<Transaction>> {
    return this.get<Transaction>(this.buildEndpoint(id));
  }
  
  /**
   * Create a new transaction
   */
  async createTransaction(transaction: TransactionCreate): Promise<ServiceResponse<Transaction>> {
    return this.post<Transaction>(this.baseEndpoint, transaction);
  }
  
  /**
   * Update an existing transaction
   */
  async updateTransaction(id: string, transaction: TransactionUpdate): Promise<ServiceResponse<Transaction>> {
    return this.put<Transaction>(this.buildEndpoint(id), transaction);
  }
  
  /**
   * Delete a transaction
   */
  async deleteTransaction(id: string): Promise<ServiceResponse<{ message: string }>> {
    return this.delete<{ message: string }>(this.buildEndpoint(id));
  }
  
  /**
   * Get transaction statistics
   */
  async getTransactionStats(filters?: TransactionFilters): Promise<ServiceResponse<TransactionStats>> {
    const params = this.buildParams(filters || {});
    return this.get<TransactionStats>(this.buildEndpoint('stats'), params);
  }
  
  /**
   * Search transactions with advanced query
   */
  async searchTransactions(request: TransactionSearchRequest): Promise<ServiceResponse<TransactionListResponse>> {
    const params = this.buildParams(request);
    return this.get<TransactionListResponse>(this.buildEndpoint('search'), params);
  }
  
  /**
   * Get transaction categories (for filtering)
   */
  async getTransactionCategories(): Promise<ServiceResponse<string[]>> {
    return this.get<string[]>(this.buildEndpoint('categories'));
  }
  
  /**
   * Import transactions from CSV
   */
  async importCSV(file: File, accountId?: string): Promise<ServiceResponse<CSVImportResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (accountId) {
      formData.append('account_id', accountId);
    }
    
    return this.postFormData<CSVImportResponse>(this.buildEndpoint('import'), formData);
  }
  
  /**
   * Export transactions to CSV/JSON
   */
  async exportTransactions(filters: ExportFilters): Promise<ServiceResponse<Blob>> {
    const params = this.buildParams(filters);
    return this.getBlob(this.buildEndpoint('export'), params);
  }
  
  /**
   * Bulk delete transactions
   */
  async bulkDeleteTransactions(request: BulkDeleteRequest): Promise<ServiceResponse<BulkDeleteResponse>> {
    return this.post<BulkDeleteResponse>(this.buildEndpoint('bulk-delete'), request);
  }
  
  /**
   * Get recent transactions (simplified)
   */
  async getRecentTransactions(limit: number = 10): Promise<ServiceResponse<Transaction[]>> {
    const params = { limit: limit.toString(), sort_by: 'created_at', sort_order: 'desc' };
    const response = await this.get<TransactionListResponse>(this.baseEndpoint, params);
    
    if (response.success && response.data) {
      return {
        ...response,
        data: response.data.items
      };
    }
    
    return response as ServiceResponse<Transaction[]>;
  }
  
  /**
   * Get transactions by category
   */
  async getTransactionsByCategory(categoryId: string, filters?: Omit<TransactionFilters, 'category_id'>): Promise<ServiceResponse<TransactionListResponse>> {
    const params = this.buildParams({ ...filters, category_id: categoryId });
    return this.get<TransactionListResponse>(this.baseEndpoint, params);
  }
  
  /**
   * Get transactions by account
   */
  async getTransactionsByAccount(accountId: string, filters?: Omit<TransactionFilters, 'account_id'>): Promise<ServiceResponse<TransactionListResponse>> {
    const params = this.buildParams({ ...filters, account_id: accountId });
    return this.get<TransactionListResponse>(this.baseEndpoint, params);
  }
  
  /**
   * Get transactions by date range
   */
  async getTransactionsByDateRange(
    startDate: string, 
    endDate: string, 
    filters?: Omit<TransactionFilters, 'start_date' | 'end_date'>
  ): Promise<ServiceResponse<TransactionListResponse>> {
    const params = this.buildParams({ 
      ...filters, 
      start_date: startDate, 
      end_date: endDate 
    });
    return this.get<TransactionListResponse>(this.baseEndpoint, params);
  }
  
  /**
   * Get spending trends data
   */
  async getSpendingTrends(period: 'week' | 'month' | 'year' = 'month'): Promise<ServiceResponse<SpendingTrend[]>> {
    const params = { period };
    return this.get<SpendingTrend[]>(this.buildEndpoint('trends'), params);
  }
  
  /**
   * Get category breakdown
   */
  async getCategoryBreakdown(filters?: TransactionFilters): Promise<ServiceResponse<any[]>> {
    const params = this.buildParams(filters || {});
    return this.get<any[]>(this.buildEndpoint('category-breakdown'), params);
  }
}

// Create and export singleton instance
export const transactionService = new StandardizedTransactionService();