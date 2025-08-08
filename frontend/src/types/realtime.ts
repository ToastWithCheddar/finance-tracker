export interface AccountSummary {
  account_id: string;
  account_name: string;
  account_type: string;
  balance_cents: number;
  currency: string;
}

export interface CategorySpending {
  category_id: string;
  category_name: string;
  category_emoji?: string;
  amount_cents: number;
  transaction_count: number;
  percentage: number;
}

export interface DashboardData {
    total_balance: number;
    monthly_spending: number;
    monthly_income: number;
    budget_utilization: number;
    active_goals: number;
    recent_transactions: RealtimeTransaction[];
    account_summary: AccountSummary[];
    spending_by_category: CategorySpending[];
    updated_at: string;
  }
  
  export interface RealtimeTransaction {
    id: string;
    amount_cents: number;
    description: string;
    merchant?: string;
    category_id?: string;
    category_name?: string;
    category_emoji?: string;
    account_id: string;
    account_name?: string;
    transaction_date: string;
    created_at: string;
    is_income: boolean;
    isNew?: boolean; // For highlighting new transactions
  }
  
  export interface RealtimeNotification {
    id: string;
    title: string;
    message: string;
    type: 'success' | 'error' | 'warning' | 'info' | 'budget_alert' | 'goal_achieved';
    priority: 'low' | 'medium' | 'high' | 'critical';
    action_url?: string;
    metadata?: Record<string, unknown>;
    created_at: string;
    read: boolean;
    isNew?: boolean;
  }
  
  export interface AccountBalance {
    account_id: string;
    account_name: string;
    old_balance_cents: number;
    new_balance_cents: number;
    change_cents: number;
    updated_at: string;
  }
  
  export interface BudgetAlert {
    budget_id: string;
    budget_name: string;
    category_name?: string;
    amount_cents: number;
    spent_cents: number;
    remaining_cents: number;
    percentage_used: number;
    alert_type: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    threshold_reached: boolean;
  }
  
  export interface GoalProgress {
    goal_id: string;
    goal_name: string;
    target_amount_cents: number;
    current_amount_cents: number;
    remaining_cents: number;
    progress_percentage: number;
    target_date?: string;
    is_achieved: boolean;
    milestone_reached: boolean;
  }
  
  export interface ConnectionStatus {
    status: 'connecting' | 'connected' | 'disconnected' | 'failed';
    lastConnected?: Date;
    lastDisconnected?: Date;
    reconnectAttempts: number;
  }