
export interface Transaction {
  id: string;
  userId: string;
  user_id?: string; // Backend field name
  accountId: string;
  account_id?: string; // Backend field name  
  accountName: string;
  account_name?: string; // Backend field name
  accountType?: string;
  account_type?: string; // Backend field name
  categoryId?: string;
  category_id?: string; // Backend field name
  categoryName?: string;
  category_name?: string; // Backend field name
  amountCents: number;
  amount_cents?: number; // Backend field name
  currency: string;
  description: string;
  merchant?: string;
  transactionDate: string;
  transaction_date?: string | Date; // Backend field name - can be Date or string
  location?: {
    lat: number;
    lng: number;
    address: string;
  };
  notes?: string;
  tags?: string[];
  plaidTransactionId?: string;
  plaid_transaction_id?: string; // Backend field name
  confidenceScore?: number;
  confidence_score?: number; // Backend field name
  createdAt: string;
  created_at?: string; // Backend field name
  updatedAt: string;
  updated_at?: string; // Backend field name
  status?: string; // Backend field
  isTransfer?: boolean;
  is_transfer?: boolean; // Backend field name
  mlSuggestedCategoryId?: string;
  ml_suggested_category_id?: string; // Backend field name
}

export interface CreateTransactionRequest {
  accountId: string;
  categoryId?: string;
  category_id?: string; // Backend field name
  amountCents: number;
  amount?: number; // Frontend convenience field (dollars)
  currency?: string;
  description: string;
  merchant?: string;
  transactionDate: string;
  transaction_date?: string; // Backend field name
  transaction_type: 'income' | 'expense';
  notes?: string;
  tags?: string[];
  [key: string]: unknown;
}

export interface UpdateTransactionRequest extends Partial<CreateTransactionRequest> {
  id: string;
}

// Removed: TransactionGroupBy - no longer using grouping functionality

export interface TransactionFilters {
  accountId?: string;
  account_id?: string; // Backend compatibility
  categoryId?: string;
  category_id?: string; // Backend compatibility
  dateFrom?: string;
  dateTo?: string;
  start_date?: string; // Backend compatibility
  end_date?: string; // Backend compatibility
  amountMinCents?: number;
  amountMaxCents?: number;
  min_amount_cents?: number; // Backend compatibility
  max_amount_cents?: number; // Backend compatibility
  tags?: string[];
  search?: string;
  search_query?: string; // Backend compatibility
  page?: number;
  per_page?: number;
  limit?: number;
  // Removed: group_by - no longer using grouping functionality
  transaction_type?: 'income' | 'expense';
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

// Deprecated: TransactionGroup - kept for backend API compatibility
export interface TransactionGroup {
  key: string;
  total_amount_cents: number;
  count: number;
  transactions: Transaction[];
}

// Deprecated: TransactionGroupedResponse - kept for backend API compatibility
export interface TransactionGroupedResponse {
  groups: TransactionGroup[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  grouped: boolean;
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
