export interface RecurringRule {
  frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'yearly';
  interval: number;
  endDate?: string;
  dayOfWeek?: number; // 0-6 for weekly
  dayOfMonth?: number; // 1-31 for monthly
  monthOfYear?: number; // 1-12 for yearly
}

export interface Transaction {
  id: string;
  userId: string;
  accountId: string;
  accountName: string;
  accountType: string;
  categoryId?: string;
  amountCents: number;
  currency: string;
  description: string;
  merchant?: string;
  transactionDate: string;
  isRecurring: boolean;
  recurringRule?: RecurringRule;
  location?: {
    lat: number;
    lng: number;
    address: string;
  };
  notes?: string;
  tags?: string[];
  plaidTransactionId?: string;
  confidenceScore?: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTransactionRequest {
  accountId: string;
  categoryId?: string;
  amountCents: number;
  currency?: string;
  description: string;
  merchant?: string;
  transactionDate: string;
  isRecurring?: boolean;
  recurringRule?: RecurringRule;
  notes?: string;
  tags?: string[];
  [key: string]: unknown;
}

export interface UpdateTransactionRequest extends Partial<CreateTransactionRequest> {
  id: string;
}

export interface TransactionFilters {
  accountId?: string;
  categoryId?: string;
  merchant?: string;
  dateFrom?: string;
  dateTo?: string;
  amountMinCents?: number;
  amountMaxCents?: number;
  tags?: string[];
  search?: string;
  page?: number;
  per_page?: number;
  limit?: number;
}

export interface TransactionSummary {
  totalIncome: number;
  totalExpenses: number;
  netAmount: number;
}

// Alias for backward compatibility
export type TransactionCreate = CreateTransactionRequest;
export type TransactionUpdate = UpdateTransactionRequest;

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface TransactionStats {
  total_count: number;
  total_income: number;
  total_expenses: number;
  net_amount: number;
  average_transaction: number;
  transaction_count_by_type: {
    income: number;
    expense: number;
  };
}

export interface CategorySum {
  categoryId: string;
  categoryName: string;
  totalAmount: number;
  transactionCount: number;
  percentage: number;
}