export interface UnifiedSubscription {
  // Common identifiers
  id: string;
  name: string;
  description: string;
  
  // Financial data  
  amountCents: number;
  amountDollars: number;
  currency: string;
  monthlyEstimatedCents: number;
  
  // Scheduling
  frequency: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY';
  nextDueDate: string;
  lastTransactionDate?: string;
  
  // Categorization
  categoryName?: string;
  categoryId?: string;
  
  // Source tracking
  source: 'plaid' | 'manual';
  sourceId: string; // Original ID from Plaid or manual rules
  
  // Status and management
  isActive: boolean;
  isMuted?: boolean; // For Plaid subscriptions
  isLinked?: boolean; // Whether Plaid subscription is linked to manual rule
  linkedRuleId?: string;
  
  // Account information
  accountId: string;
  accountName?: string;
  merchantName?: string;
  
  // Insights (future backend integration)
  insights?: {
    isLowUsage?: boolean;
    priceChangeDetected?: boolean;
    lastPriceChange?: { 
      fromCents: number; 
      toCents: number; 
      date: string 
    };
    usageScore?: number; // 0-100 scale
    confidenceScore?: number;
  };
  
  // Metadata
  createdAt: string;
  updatedAt: string;
}

export interface SubscriptionAnalytics {
  totalMonthlyCents: number;
  totalAnnualCents: number;
  subscriptionCount: number;
  activeSubscriptionCount: number;
  categoryBreakdown: Array<{
    categoryId: string;
    categoryName: string;
    amountCents: number;
    count: number;
    percentage: number;
  }>;
  frequencyBreakdown: Record<string, {
    count: number;
    totalCents: number;
  }>;
  sourceBreakdown: {
    plaid: { count: number; totalCents: number };
    manual: { count: number; totalCents: number };
  };
  insights: {
    potentialSavingsCents: number;
    unusedSubscriptions: number;
    priceIncreases: number;
    averageSubscriptionCents: number;
  };
}

export interface UnifiedSubscriptionFilter {
  // General filters
  search?: string;
  source?: 'plaid' | 'manual' | 'all';
  isActive?: boolean;
  frequency?: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY';
  
  // Financial filters
  minAmountCents?: number;
  maxAmountCents?: number;
  
  // Category filters
  categoryId?: string;
  accountId?: string;
  
  // Date filters
  nextDueFrom?: string;
  nextDueTo?: string;
  
  // Status filters
  isMuted?: boolean;
  isLinked?: boolean;
  hasInsights?: boolean;
  
  // Specific filters for underlying data sources
  plaidFilters?: {
    include_muted?: boolean;
    status_filter?: 'MATURE' | 'EARLY_DETECTION' | 'INACCURATE' | 'TERMINATED';
    linked_to_rule?: boolean;
  };
  ruleFilters?: {
    is_confirmed?: boolean;
    next_due_from?: string;
    next_due_to?: string;
  };
}

export interface SubscriptionInsight {
  id: string;
  subscriptionId: string;
  type: 'low_usage' | 'price_increase' | 'duplicate_detected' | 'cancellation_suggested';
  severity: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  potentialSavingsCents?: number;
  actionRecommended?: string;
  createdAt: string;
  isRead: boolean;
  isDismissed: boolean;
}

export interface SubscriptionCostTrend {
  month: string;
  totalCents: number;
  subscriptionCount: number;
  newSubscriptions: number;
  cancelledSubscriptions: number;
}

export interface SubscriptionActions {
  mute?: (id: string, muted: boolean) => Promise<void>;
  link?: (plaidId: string, ruleId: string) => Promise<void>;
  unlink?: (plaidId: string) => Promise<void>;
  edit?: (id: string, updates: any) => Promise<void>;
  delete?: (id: string) => Promise<void>;
  createFromSuggestion?: (suggestion: any) => Promise<void>;
}

// Utility types for mapping
export interface PlaidToUnifiedMapping {
  id: string;
  name: string;
  description: string;
  amountCents: number;
  amountDollars: number;
  currency: string;
  monthlyEstimatedCents: number;
  frequency: string;
  nextDueDate: string;
  categoryName?: string;
  accountId: string;
  merchantName?: string;
  isActive: boolean;
  isMuted: boolean;
  isLinked: boolean;
  linkedRuleId?: string;
  lastTransactionDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ManualToUnifiedMapping {
  id: string;
  name: string;
  description: string;
  amountCents: number;
  amountDollars: number;
  currency: string;
  frequency: string;
  nextDueDate: string;
  categoryId?: string;
  accountId: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}