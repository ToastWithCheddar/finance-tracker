// There could be a better way to do this, but this is a quick and dirty solution to get the types working
export const GoalStatus = {
    ACTIVE : 'active',
    COMPLETED : 'completed',
    PAUSED : 'paused',
    CANCELLED : 'cancelled'
  } as const;
  export type GoalStatus = typeof GoalStatus[keyof typeof GoalStatus];
  
  export const GoalType = {
    SAVINGS : 'savings',
    DEBT_PAYOFF : 'debt_payoff',
    EMERGENCY_FUND : 'emergency_fund',
    PURCHASE : 'purchase',
    INVESTMENT : 'investment',
    OTHER : 'other'
  } as const;
  export type GoalType = typeof GoalType[keyof typeof GoalType];
  
  export const GoalPriority = {
    LOW : 'low',
    MEDIUM : 'medium',
    HIGH : 'high',
    CRITICAL : 'critical'
  } as const;
  export type GoalPriority = typeof GoalPriority[keyof typeof GoalPriority];
  
  export const ContributionFrequency = {
    DAILY : 'daily',
    WEEKLY : 'weekly',
    MONTHLY : 'monthly',
    QUARTERLY : 'quarterly',
    YEARLY : 'yearly'
  } as const;
  export type ContributionFrequency = typeof ContributionFrequency[keyof typeof ContributionFrequency];
  
  export interface GoalContribution {
    id: string;
    goal_id: string;
    amount_cents: number;
    amount: number; // Computed property for backwards compatibility
    contribution_date: string;
    note?: string;
    is_automatic: boolean;
    transaction_id?: string;
    created_at: string;
  }
  
  export interface GoalMilestone {
    id: string;
    goal_id: string;
    percentage: number;
    amount_reached_cents: number;
    reached_date: string;
    celebrated: boolean;
    celebration_message?: string;
    created_at: string;
  }
  
  export interface Goal {
    id: string;
    user_id: string;
    name: string;
    description?: string;
    target_amount_cents: number;
    current_amount_cents: number;
    goal_type: GoalType;
    priority: GoalPriority;
    status: GoalStatus;
    start_date: string;
    target_date?: string;
    completed_date?: string;
    last_contribution_date?: string;
    contribution_frequency?: ContributionFrequency;
    monthly_target_cents?: number;
    auto_contribute: boolean;
    auto_contribution_amount_cents?: number;
    auto_contribution_source?: string;
    milestone_percentage: number;
    last_milestone_reached: number;
    created_at: string;
    updated_at: string;
    
    // Computed properties
    progress_percentage: number;
    remaining_amount_cents: number;
    remaining_amount: number; // Computed property for backwards compatibility (dollars)
    is_completed: boolean;
    days_remaining?: number;
    
    // Related data
    contributions: GoalContribution[];
    milestones: GoalMilestone[];
  }
  
  export interface GoalCreate {
    name: string;
    description?: string;
    target_amount_cents: number;
    goal_type: GoalType;
    priority?: GoalPriority;
    target_date?: string;
    contribution_frequency?: ContributionFrequency;
    monthly_target_cents?: number;
    auto_contribute?: boolean;
    auto_contribution_amount_cents?: number;
    auto_contribution_source?: string;
    milestone_percentage?: number;
    [key: string]: unknown;
  }
  
  export interface GoalUpdate {
    name?: string;
    description?: string;
    target_amount_cents?: number;
    goal_type?: GoalType;
    priority?: GoalPriority;
    status?: GoalStatus;
    target_date?: string;
    contribution_frequency?: ContributionFrequency;
    monthly_target_cents?: number;
    auto_contribute?: boolean;
    auto_contribution_amount_cents?: number;
    auto_contribution_source?: string;
    milestone_percentage?: number;
    [key: string]: unknown;
  }
  
  export interface GoalContributionCreate {
    amount_cents: number;
    note?: string;
    [key: string]: unknown;
  }
  
  export interface GoalsResponse {
    goals: Goal[];
    total: number;
    active_goals: number;
    completed_goals: number;
    total_target_amount_cents: number;
    total_current_amount_cents: number;
    overall_progress: number;
    total_goals: number;
    paused_goals: number;
    average_progress: number;
    goals_by_type: Record<string, {
      count: number;
      total_amount_cents: number;
      current_amount_cents: number;
    }>;
    goals_by_priority: Record<string, {
      count: number;
      total_amount_cents: number;
      current_amount_cents: number;
    }>;
  }
  
  export interface GoalStats {
    total_goals: number;
    active_goals: number;
    completed_goals: number;
    paused_goals: number;
    total_saved_cents: number;
    total_target_cents: number;
    average_progress: number;
    this_month_contributions_cents: number;
    goals_by_type: Record<string, any>;
    goals_by_priority: Record<string, any>;
    contribution_stats: {
      total_contributions_cents: number;
      this_month_cents: number;
      last_month_cents: number;
      average_monthly_cents: number;
      contribution_trend: Array<{
        month: string;
        amount_cents: number;
      }>;
    };
  }
  
  export interface MilestoneAlert {
    goal_id: string;
    goal_name: string;
    milestone_percentage: number;
    amount_reached_cents: number;
    celebration_message: string;
    reached_date: string;
  }
  
  export interface GoalTypeOption {
    value: GoalType;
    label: string;
    icon: string;
  }
  
  export interface PriorityOption {
    value: GoalPriority;
    label: string;
    color: string;
  }
  
  export interface FrequencyOption {
    value: string;
    label: string;
  }
  
  // Filter types
  export interface GoalFilters {
    status?: GoalStatus;
    goal_type?: GoalType;
    priority?: GoalPriority;
    skip?: number;
    limit?: number;
  }