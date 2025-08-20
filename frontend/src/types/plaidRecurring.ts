// Plaid recurring transactions types
export interface PlaidRecurringTransaction {
  plaid_recurring_transaction_id: string;
  user_id: string;
  account_id: string;
  
  // Plaid fields
  description: string;
  merchant_name?: string;
  amount_cents: number;
  amount_dollars: number;
  currency: string;
  
  plaid_frequency: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'ANNUALLY' | 'UNKNOWN';
  plaid_status: 'MATURE' | 'EARLY_DETECTION' | 'INACCURATE' | 'TERMINATED';
  plaid_category?: string[];
  
  // Computed fields from Plaid
  last_amount_cents: number;
  last_date: string;
  monthly_estimated_amount_cents: number;
  
  // User management fields
  is_muted: boolean;
  is_linked_to_rule: boolean;
  linked_rule_id?: string;
  
  // Metadata
  is_mature: boolean;
  first_detected_at: string;
  last_sync_at: string;
  sync_count: number;
  created_at: string;
  updated_at: string;
}

export interface PlaidRecurringFilter {
  include_muted?: boolean;
  account_id?: string;
  status_filter?: 'MATURE' | 'EARLY_DETECTION' | 'INACCURATE' | 'TERMINATED';
  frequency_filter?: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'ANNUALLY';
  min_amount_cents?: number;
  max_amount_cents?: number;
  linked_to_rule?: boolean;
  search?: string;
}

export interface PlaidRecurringSyncResult {
  success: boolean;
  accounts_processed: number;
  total_recurring_transactions: number;
  new_recurring_transactions: number;
  updated_recurring_transactions: number;
  total_errors: number;
  error?: string;
  results: PlaidRecurringTransaction[];
}

export interface PlaidRecurringInsights {
  total_subscriptions: number;
  active_subscriptions: number;
  muted_subscriptions: number;
  linked_subscriptions: number;
  
  total_monthly_cost_cents: number;
  total_monthly_cost_dollars: number;
  
  frequency_breakdown: {
    [key: string]: number;
  };
  
  status_breakdown: {
    [key: string]: number;
  };
  
  top_subscriptions: {
    plaid_recurring_transaction_id: string;
    description: string;
    merchant_name?: string;
    monthly_estimated_amount_cents: number;
    frequency: string;
  }[];
  
  cost_by_account: {
    account_id: string;
    account_name: string;
    total_monthly_cents: number;
    subscription_count: number;
  }[];
}

export interface PlaidRecurringStats {
  total_recurring_transactions: number;
  active_recurring_transactions: number;
  mature_recurring_transactions: number;
  linked_recurring_transactions: number;
  total_monthly_cost_cents: number;
  total_monthly_cost_dollars: number;
}

export interface PlaidRecurringBulkMuteRequest {
  plaid_recurring_ids: string[];
  muted: boolean;
}

export interface PlaidRecurringBulkMuteResult {
  updated_count: number;
  failed_count: number;
  failed_ids: string[];
  action: 'muted' | 'unmuted';
}

export interface PlaidRecurringPotentialMatch {
  rule_id: string;
  rule_name: string;
  match_score: number;
  matching_conditions: string[];
  suggested_changes?: {
    amount_cents?: number;
    frequency?: string;
    tolerance_cents?: number;
  };
}