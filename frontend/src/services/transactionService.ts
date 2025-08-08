import { BaseService } from './base/BaseService';
import { apiClient } from './api';
import type { 
  Transaction, 
  CreateTransactionRequest, 
  UpdateTransactionRequest, 
  TransactionFilters,
  TransactionSummary
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

    return this.get<TransactionListResponse>(
      this.buildEndpoint('/'),
      params,
      {
        useCache: options?.useCache ?? true,
        cacheTtl: 2 * 60 * 1000, // 2 minutes cache for transactions
        context: options?.context
      }
    );
  }

  async getTransaction(
    transactionId: string,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<Transaction> {
    return this.get<Transaction>(
      this.buildEndpoint(`/${transactionId}`),
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
      this.buildEndpoint('/'),
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
      this.buildEndpoint(`/${transactionId}`),
      transaction,
      { context: options?.context }
    );
  }

  async deleteTransaction(
    transactionId: string,
    options?: { context?: ErrorContext }
  ): Promise<{ message: string }> {
    return this.delete<{ message: string }>(
      this.buildEndpoint(`/${transactionId}`),
      { context: options?.context }
    );
  }

  async bulkDeleteTransactions(
    transactionIds: string[],
    options?: { context?: ErrorContext }
  ): Promise<{ message: string; deleted_count: number }> {
    return this.post<{ message: string; deleted_count: number }>(
      this.buildEndpoint('/bulk-delete'),
      { transaction_ids: transactionIds },
      { context: options?.context }
    );
  }

  async getTransactionStats(
    filters?: TransactionFilters,
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<TransactionSummary> {
    const params: Record<string, string | number | boolean> = {};
    
    if (filters?.dateFrom) params.start_date = filters.dateFrom;
    if (filters?.dateTo) params.end_date = filters.dateTo;
    if (filters?.categoryId) params.category_id = filters.categoryId;
    if (filters?.search) params.search_query = filters.search;

    return this.get<TransactionSummary>(
      this.buildEndpoint('/analytics/stats'),
      params,
      {
        useCache: options?.useCache ?? true,
        cacheTtl: 5 * 60 * 1000, // 5 minutes cache for stats
        context: options?.context
      }
    );
  }

  async importCSV(
    file: File,
    options?: { context?: ErrorContext }
  ): Promise<CSVImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Use apiClient directly for FormData uploads
      const result = await apiClient.postFormData<CSVImportResponse>(
        this.buildEndpoint('/import/csv'),
        formData
      );
      
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
    
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.category_id) params.category_id = filters.category_id;
    if (filters.transaction_type) params.transaction_type = filters.transaction_type;

    try {
      return await apiClient.getBlob('/transactions/export', params);
    } catch (error) {
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
            const mappedTransaction: CreateTransactionRequest = {
              accountId: transaction.account_id || transaction.accountId || '', // Will need to be set by caller
              amountCents: Math.round(amount * 100), // Convert dollars to cents
              description: transaction.description || transaction.Description || '',
              transactionDate: transaction.date || transaction.Date || transaction.transaction_date || new Date().toISOString().split('T')[0],
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
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
}

export const transactionService = new TransactionService();