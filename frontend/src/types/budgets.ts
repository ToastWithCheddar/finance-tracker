export interface Budget {
    id: string;
    user_id: string;
    category_id?: string;
    category_name?: string;
    name: string;
    amount_cents: number;
    period: BudgetPeriod;
    start_date: string;
    end_date?: string;
    alert_threshold: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    usage?: BudgetUsage;
    has_custom_alerts?: boolean;
  }
  
  export interface BudgetUsage {
    budget_id: string;
    spent_cents: number;
    remaining_cents: number;
    percentage_used: number;
    is_over_budget: boolean;
    days_remaining?: number;
  }
  
  export interface BudgetAlert {
    budget_id: string;
    budget_name: string;
    category_name?: string;
    alert_type: 'warning' | 'exceeded' | 'near_end';
    message: string;
    percentage_used: number;
    amount_over?: number;
  }
  
  export interface BudgetSummary {
    total_budgets: number;
    active_budgets: number;
    total_budgeted_cents: number;
    total_spent_cents: number;
    total_remaining_cents: number;
    over_budget_count: number;
    alert_count: number;
  }
  
  export interface BudgetProgress {
    budget_id: string;
    budget_name: string;
    period_start: string;
    period_end: string;
    daily_spending: Array<{ date: string; amount_cents: number }>;
    weekly_spending: Array<{ week: string; amount_cents: number }>;
    category_breakdown: Array<{ category: string; amount_cents: number; percentage: number }>;
  }
  
  export const BudgetPeriod = {
    WEEKLY : 'weekly',
    MONTHLY : 'monthly',
    QUARTERLY : 'quarterly',
    YEARLY :'yearly'
  } as const;
  export type BudgetPeriod = typeof BudgetPeriod[keyof typeof BudgetPeriod];
  
  export interface CreateBudgetRequest {
    name: string;
    category_id?: string;
    amount_cents: number;
    period: BudgetPeriod;
    start_date: string;
    end_date?: string;
    alert_threshold?: number;
    is_active?: boolean;
    [key: string]: unknown;
  }
  
  export type UpdateBudgetRequest = Partial<CreateBudgetRequest>;
  
  export interface BudgetFilters {
    category_id?: string;
    period?: BudgetPeriod;
    is_active?: boolean;
    over_budget?: boolean;
    skip?: number;
    limit?: number;
  }
  
  export interface BudgetListResponse {
    budgets: Budget[];
    summary: BudgetSummary;
    alerts: BudgetAlert[];
  }

  // Budget Alert Settings interfaces
  export interface BudgetAlertSettings {
    id: string;
    budget_id: string;
    user_id: string;
    alerts_enabled: boolean;
    alert_thresholds: number[];
    email_alerts: boolean;
    push_alerts: boolean;
    in_app_alerts: boolean;
    alert_frequency: 'immediate' | 'daily' | 'weekly';
    suppress_repeated_alerts: boolean;
    end_of_period_warning: boolean;
    end_warning_days: number;
    smart_pacing_alerts: boolean;
    milestone_celebration: boolean;
    custom_alert_messages?: Record<string, any>;
    created_at: string;
    updated_at: string;
  }

  export interface CreateBudgetAlertSettingsRequest {
    alerts_enabled?: boolean;
    alert_thresholds?: number[];
    email_alerts?: boolean;
    push_alerts?: boolean;
    in_app_alerts?: boolean;
    alert_frequency?: 'immediate' | 'daily' | 'weekly';
    suppress_repeated_alerts?: boolean;
    end_of_period_warning?: boolean;
    end_warning_days?: number;
    smart_pacing_alerts?: boolean;
    milestone_celebration?: boolean;
    custom_alert_messages?: Record<string, any>;
  }

  export type UpdateBudgetAlertSettingsRequest = Partial<CreateBudgetAlertSettingsRequest>;

  export interface BudgetAlertPreview {
    threshold: number;
    message: string;
    priority: string;
    channels: string[];
  }

  export interface BudgetAlertTest {
    budget_id: string;
    test_threshold: number;
    test_amount_cents: number;
  }

  // Budget Calendar interfaces
  export interface BudgetCalendarDay {
    date: string;
    daily_spending_limit_cents: number;
    actual_spending_cents: number;
    percentage_used: number;
    is_over_limit: boolean;
    transactions_count: number;
  }

  export interface BudgetCalendarResponse {
    budget_id: string;
    budget_name: string;
    month: string; // YYYY-MM format
    period_start: string;
    period_end: string;
    daily_data: BudgetCalendarDay[];
    summary: {
      total_spending_cents: number;
      total_limit_cents: number;
      days_in_month: number;
      days_with_budget: number;
      days_over_limit: number;
      average_daily_spending_cents: number;
      month_progress_percentage: number;
    };
  }