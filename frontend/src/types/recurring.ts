export interface RecurringTransactionRule {
  id: string;
  user_id: string;
  account_id: string;
  category_id: string | null;
  
  name: string;
  description: string;
  amount_cents: number;
  currency: string;
  
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annually';
  interval: number;
  
  start_date: string;
  end_date: string | null;
  next_due_date: string;
  last_generated_date: string | null;
  last_matched_at: string | null;
  
  tolerance_cents: number;
  auto_categorize: boolean;
  generate_notifications: boolean;
  
  is_active: boolean;
  is_confirmed: boolean;
  confidence_score: number | null;
  detection_method: string | null;
  
  created_at: string;
  updated_at: string;
  
  // Computed fields
  amount_dollars: number;
  days_until_next: number | null;
}

export interface RecurringSuggestion {
  id: string;
  merchant: string;
  normalized_merchant: string;
  
  amount_cents: number;
  amount_dollars: number;
  currency: string;
  
  frequency: string;
  interval: number;
  confidence_score: number;
  
  account_id: string;
  category_id: string | null;
  
  transaction_count: number;
  sample_dates: string[];
  next_expected_date: string;
  
  amount_variation: {
    min_cents: number;
    max_cents: number;
    std_dev_cents: number;
  };
  detection_method: string;
}

export interface SuggestionApproval {
  suggestion_id: string;
  name?: string;
  category_id?: string;
  amount_cents?: number;
  tolerance_cents?: number;
  auto_categorize?: boolean;
  generate_notifications?: boolean;
}

export interface RecurringTransactionRuleCreate {
  account_id: string;
  category_id?: string;
  
  name: string;
  description: string;
  amount_cents: number;
  currency: string;
  
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annually';
  interval: number;
  
  start_date: string;
  end_date?: string;
  
  tolerance_cents: number;
  auto_categorize: boolean;
  generate_notifications: boolean;
  
  notification_settings?: Record<string, any>;
  custom_rule?: Record<string, any>;
}

export interface RecurringTransactionRuleUpdate {
  name?: string;
  description?: string;
  amount_cents?: number;
  currency?: string;
  
  frequency?: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annually';
  interval?: number;
  
  end_date?: string | null;
  next_due_date?: string;
  
  tolerance_cents?: number;
  auto_categorize?: boolean;
  generate_notifications?: boolean;
  is_active?: boolean;
  
  category_id?: string;
  notification_settings?: Record<string, any>;
  custom_rule?: Record<string, any>;
}

export interface RecurringRuleFilter {
  is_active?: boolean;
  is_confirmed?: boolean;
  frequency?: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annually';
  account_id?: string;
  category_id?: string;
  
  next_due_from?: string;
  next_due_to?: string;
  
  min_amount_cents?: number;
  max_amount_cents?: number;
  
  search?: string;
}

export interface PaginatedRecurringRulesResponse {
  items: RecurringTransactionRule[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  
  // Summary statistics
  active_rules: number;
  upcoming_in_week: number;
  total_monthly_amount_cents: number;
}

export interface RecurringRuleStats {
  total_rules: number;
  active_rules: number;
  inactive_rules: number;
  confirmed_rules: number;
  suggested_rules: number;
  
  // By frequency
  weekly_count: number;
  monthly_count: number;
  quarterly_count: number;
  annual_count: number;
  
  // Financial stats
  total_monthly_amount_cents: number;
  average_amount_cents: number;
  
  // Upcoming
  due_this_week: number;
  due_next_week: number;
  overdue: number;
}

// UI State interfaces
export interface RecurringRulesState {
  rules: RecurringTransactionRule[];
  suggestions: RecurringSuggestion[];
  stats: RecurringRuleStats | null;
  filters: RecurringRuleFilter;
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
  loading: {
    rules: boolean;
    suggestions: boolean;
    stats: boolean;
    actions: boolean;
  };
  error: string | null;
}

// Form interfaces
export interface RecurringRuleFormData {
  account_id: string;
  category_id: string;
  name: string;
  description: string;
  amount_dollars: string;
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annually';
  interval: number;
  start_date: string;
  end_date: string;
  tolerance_dollars: string;
  auto_categorize: boolean;
  generate_notifications: boolean;
}

// API Response types
export interface ApiError {
  error_code: string;
  message: string;
  details?: Record<string, any>;
}