// Categorization rules types
export interface CategorizationRule {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  priority: number;
  
  // JSON fields for flexible conditions and actions
  conditions: CategorizationRuleConditions;
  actions: CategorizationRuleActions;
  
  is_active: boolean;
  times_applied: number;
  success_rate?: number;
  last_applied_at?: string;
  
  created_at: string;
  updated_at: string;
}

export interface CategorizationRuleConditions {
  // Merchant conditions
  merchant_contains?: string[];
  merchant_exact?: string[];
  merchant_regex?: string;
  
  // Description conditions
  description_contains?: string[];
  description_exact?: string[];
  description_regex?: string;
  
  // Amount conditions
  amount_range?: {
    min_cents?: number;
    max_cents?: number;
  };
  amount_exact?: number;
  
  // Account conditions
  account_type?: string[];
  account_id?: string[];
  
  // Transaction type conditions
  transaction_type?: 'income' | 'expense' | 'transfer';
  
  // Category exclusions
  exclude_category_ids?: string[];
  
  // Date conditions
  date_range?: {
    start_date?: string;
    end_date?: string;
  };
  
  // Day of week/month conditions
  day_of_week?: number[];
  day_of_month?: number[];
  
  // Custom conditions (for advanced users)
  custom_conditions?: Record<string, any>;
}

export interface CategorizationRuleActions {
  // Category assignment
  set_category_id?: string;
  
  // Tags management
  add_tags?: string[];
  remove_tags?: string[];
  
  // Notes
  set_note?: string;
  append_note?: string;
  
  // Confidence scoring
  set_confidence?: number;
  
  // Auto-categorization flag
  mark_as_auto_categorized?: boolean;
  
  // Custom actions
  custom_actions?: Record<string, any>;
}

export interface CategorizationRuleCreate {
  name: string;
  description?: string;
  priority?: number;
  conditions: CategorizationRuleConditions;
  actions: CategorizationRuleActions;
  is_active?: boolean;
}

export interface CategorizationRuleUpdate {
  name?: string;
  description?: string;
  priority?: number;
  conditions?: CategorizationRuleConditions;
  actions?: CategorizationRuleActions;
  is_active?: boolean;
}

export interface CategorizationRuleFilter {
  is_active?: boolean;
  priority_min?: number;
  priority_max?: number;
  target_category_id?: string;
  has_conditions?: string; // 'merchant', 'description', 'amount', etc.
  created_after?: string;
  created_before?: string;
  search?: string;
}

export interface PaginatedCategorizationRulesResponse {
  items: CategorizationRule[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface CategorizationRuleTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  conditions_template: CategorizationRuleConditions;
  actions_template: CategorizationRuleActions;
  is_official: boolean;
  default_priority: number;
  popularity_score: number;
  created_at: string;
  updated_at: string;
}

export interface RuleTemplateCustomization {
  name?: string;
  description?: string;
  target_category_id?: string;
  priority?: number;
  condition_overrides?: Partial<CategorizationRuleConditions>;
  action_overrides?: Partial<CategorizationRuleActions>;
}

export interface RuleTestResult {
  transaction_id: string;
  transaction_description: string;
  transaction_merchant?: string;
  transaction_amount_cents: number;
  transaction_date: string;
  would_match: boolean;
  match_score: number;
  matching_conditions: string[];
  proposed_actions: CategorizationRuleActions;
}

export interface RuleApplicationResult {
  success: boolean;
  rule_applied: boolean;
  rule_id?: string;
  rule_name?: string;
  changes?: Record<string, any>;
  error?: string;
  dry_run?: boolean;
}

export interface BatchRuleApplicationResult {
  success: boolean;
  transactions_processed: number;
  rules_applied: number;
  failed_applications: number;
  results: {
    transaction_id: string;
    rule_applied: boolean;
    rule_id?: string;
    rule_name?: string;
    changes?: Record<string, any>;
    error?: string;
  }[];
}

export interface RuleEffectivenessMetrics {
  rule_id: string;
  rule_name: string;
  times_applied: number;
  success_rate: number;
  total_transactions_affected: number;
  avg_confidence_score: number;
  last_applied_at?: string;
  created_at: string;
  
  // Performance over time
  applications_by_month: {
    month: string;
    applications: number;
    success_rate: number;
  }[];
  
  // Most common results
  common_categories_assigned: {
    category_id: string;
    category_name: string;
    count: number;
  }[];
  
  common_merchants_matched: {
    merchant: string;
    count: number;
  }[];
}

export interface RuleStatistics {
  total_rules: number;
  active_rules: number;
  inactive_rules: number;
  total_applications: number;
  rules_never_used: number;
  average_success_rate: number;
  most_used_rule?: {
    id: string;
    name: string;
    times_applied: number;
  };
  highest_success_rate_rule?: {
    id: string;
    name: string;
    success_rate: number;
  };
}