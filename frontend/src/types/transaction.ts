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
  transactionCount: number;
  categoryBreakdown: CategorySum[];
}

export interface CategorySum {
  categoryId: string;
  categoryName: string;
  totalAmount: number;
  transactionCount: number;
  percentage: number;
}