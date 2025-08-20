import type { 
  PlaidRecurringTransaction, 
  RecurringTransactionRule 
} from '../types';
import type { 
  UnifiedSubscription, 
  SubscriptionAnalytics,
  PlaidToUnifiedMapping,
  ManualToUnifiedMapping 
} from '../types/subscription';

// Frequency mapping utilities
const FREQUENCY_MAPPING: Record<string, 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY'> = {
  'WEEKLY': 'WEEKLY',
  'weekly': 'WEEKLY',
  'BIWEEKLY': 'BIWEEKLY', 
  'biweekly': 'BIWEEKLY',
  'MONTHLY': 'MONTHLY',
  'monthly': 'MONTHLY',
  'QUARTERLY': 'QUARTERLY',
  'quarterly': 'QUARTERLY',
  'ANNUALLY': 'ANNUALLY',
  'annually': 'ANNUALLY',
  'UNKNOWN': 'MONTHLY' // Default fallback
};

const MONTHS_PER_FREQUENCY: Record<string, number> = {
  'WEEKLY': 12 / 52,
  'BIWEEKLY': 12 / 26, 
  'MONTHLY': 1,
  'QUARTERLY': 3,
  'ANNUALLY': 12
};

export function normalizeFrequency(frequency: string): 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY' {
  return FREQUENCY_MAPPING[frequency] || 'MONTHLY';
}

export function calculateMonthlyAmount(amountCents: number, frequency: string): number {
  const normalizedFreq = normalizeFrequency(frequency);
  const monthsPerPayment = MONTHS_PER_FREQUENCY[normalizedFreq] || 1;
  return Math.round(amountCents / monthsPerPayment);
}

export function mapPlaidToUnified(plaidTransaction: PlaidRecurringTransaction): UnifiedSubscription {
  const normalizedFreq = normalizeFrequency(plaidTransaction.plaid_frequency);
  
  return {
    id: `plaid-${plaidTransaction.plaid_recurring_transaction_id}`,
    name: plaidTransaction.merchant_name || plaidTransaction.description,
    description: plaidTransaction.description,
    
    amountCents: Math.abs(plaidTransaction.amount_cents),
    amountDollars: Math.abs(plaidTransaction.amount_dollars),
    currency: plaidTransaction.currency,
    monthlyEstimatedCents: Math.abs(plaidTransaction.monthly_estimated_amount_cents),
    
    frequency: normalizedFreq,
    nextDueDate: calculateNextDueDate(plaidTransaction.last_date, normalizedFreq),
    lastTransactionDate: plaidTransaction.last_date,
    
    categoryName: plaidTransaction.plaid_category?.join(' > '),
    categoryId: undefined, // Plaid categories don't map directly to our category IDs
    
    source: 'plaid',
    sourceId: plaidTransaction.plaid_recurring_transaction_id,
    
    isActive: plaidTransaction.plaid_status === 'MATURE' || plaidTransaction.plaid_status === 'EARLY_DETECTION',
    isMuted: plaidTransaction.is_muted,
    isLinked: plaidTransaction.is_linked_to_rule,
    linkedRuleId: plaidTransaction.linked_rule_id,
    
    accountId: plaidTransaction.account_id,
    accountName: undefined, // Would need to be populated from account data
    merchantName: plaidTransaction.merchant_name,
    
    insights: {
      confidenceScore: plaidTransaction.plaid_status === 'MATURE' ? 90 : 
                      plaidTransaction.plaid_status === 'EARLY_DETECTION' ? 70 : 30
    },
    
    createdAt: plaidTransaction.created_at,
    updatedAt: plaidTransaction.updated_at
  };
}

export function mapManualToUnified(manualRule: RecurringTransactionRule): UnifiedSubscription {
  const normalizedFreq = normalizeFrequency(manualRule.frequency);
  
  return {
    id: `manual-${manualRule.id}`,
    name: manualRule.name,
    description: manualRule.description,
    
    amountCents: manualRule.amount_cents,
    amountDollars: manualRule.amount_dollars,
    currency: manualRule.currency,
    monthlyEstimatedCents: calculateMonthlyAmount(manualRule.amount_cents, manualRule.frequency),
    
    frequency: normalizedFreq,
    nextDueDate: manualRule.next_due_date,
    lastTransactionDate: manualRule.last_matched_at,
    
    categoryName: undefined, // Would need to be populated from category data
    categoryId: manualRule.category_id,
    
    source: 'manual',
    sourceId: manualRule.id,
    
    isActive: manualRule.is_active,
    isMuted: false, // Manual rules don't have mute functionality
    isLinked: false, // Manual rules are not linked (they are the target of links)
    
    accountId: manualRule.account_id,
    accountName: undefined, // Would need to be populated from account data
    merchantName: undefined,
    
    insights: {
      confidenceScore: manualRule.confidence_score || (manualRule.is_confirmed ? 95 : 60)
    },
    
    createdAt: manualRule.created_at,
    updatedAt: manualRule.updated_at
  };
}

export function consolidateSubscriptions(
  plaidTransactions: PlaidRecurringTransaction[],
  manualRules: RecurringTransactionRule[]
): UnifiedSubscription[] {
  
  // Step 1: Convert Plaid transactions to unified format
  const plaidSubscriptions = plaidTransactions.map(mapPlaidToUnified);
  
  // Step 2: Convert manual rules to unified format  
  const manualSubscriptions = manualRules.map(mapManualToUnified);
  
  // Step 3: Handle linked subscriptions (avoid duplicates)
  const linkedPlaidIds = new Set(
    plaidTransactions
      .filter(p => p.is_linked_to_rule && p.linked_rule_id)
      .map(p => p.plaid_recurring_transaction_id)
  );
  
  // Step 4: Filter out linked Plaid subscriptions (show only manual rule)
  const unlinkedPlaidSubscriptions = plaidSubscriptions.filter(
    p => !linkedPlaidIds.has(p.sourceId)
  );
  
  // Step 5: Mark manual rules that have linked Plaid subscriptions
  const linkedRuleIds = new Set(
    plaidTransactions
      .filter(p => p.is_linked_to_rule && p.linked_rule_id)
      .map(p => p.linked_rule_id!)
  );
  
  const enhancedManualSubscriptions = manualSubscriptions.map(manual => {
    if (linkedRuleIds.has(manual.sourceId)) {
      return {
        ...manual,
        isLinked: true,
        insights: {
          ...manual.insights,
          confidenceScore: 95 // Linked rules have high confidence
        }
      };
    }
    return manual;
  });
  
  // Step 6: Merge all subscriptions and sort by monthly amount (descending)
  const allSubscriptions = [...unlinkedPlaidSubscriptions, ...enhancedManualSubscriptions];
  
  return allSubscriptions.sort((a, b) => b.monthlyEstimatedCents - a.monthlyEstimatedCents);
}

export function calculateSubscriptionAnalytics(subscriptions: UnifiedSubscription[]): SubscriptionAnalytics {
  const activeSubscriptions = subscriptions.filter(s => s.isActive && !s.isMuted);
  
  // Calculate totals
  const totalMonthlyCents = activeSubscriptions.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0);
  const totalAnnualCents = totalMonthlyCents * 12;
  
  // Category breakdown
  const categoryMap = new Map<string, { amountCents: number; count: number; categoryName: string }>();
  activeSubscriptions.forEach(sub => {
    const categoryKey = sub.categoryId || sub.categoryName || 'Uncategorized';
    const categoryName = sub.categoryName || 'Uncategorized';
    
    if (!categoryMap.has(categoryKey)) {
      categoryMap.set(categoryKey, { amountCents: 0, count: 0, categoryName });
    }
    
    const category = categoryMap.get(categoryKey)!;
    category.amountCents += sub.monthlyEstimatedCents;
    category.count += 1;
  });
  
  const categoryBreakdown = Array.from(categoryMap.entries()).map(([categoryId, data]) => ({
    categoryId,
    categoryName: data.categoryName,
    amountCents: data.amountCents,
    count: data.count,
    percentage: totalMonthlyCents > 0 ? (data.amountCents / totalMonthlyCents) * 100 : 0
  })).sort((a, b) => b.amountCents - a.amountCents);
  
  // Frequency breakdown
  const frequencyBreakdown: Record<string, { count: number; totalCents: number }> = {};
  activeSubscriptions.forEach(sub => {
    if (!frequencyBreakdown[sub.frequency]) {
      frequencyBreakdown[sub.frequency] = { count: 0, totalCents: 0 };
    }
    frequencyBreakdown[sub.frequency].count += 1;
    frequencyBreakdown[sub.frequency].totalCents += sub.monthlyEstimatedCents;
  });
  
  // Source breakdown
  const plaidSubs = activeSubscriptions.filter(s => s.source === 'plaid');
  const manualSubs = activeSubscriptions.filter(s => s.source === 'manual');
  
  const sourceBreakdown = {
    plaid: {
      count: plaidSubs.length,
      totalCents: plaidSubs.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0)
    },
    manual: {
      count: manualSubs.length,
      totalCents: manualSubs.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0)
    }
  };
  
  // Insights calculations
  const mutedSubscriptions = subscriptions.filter(s => s.isMuted);
  const lowConfidenceSubscriptions = subscriptions.filter(s => 
    s.insights?.confidenceScore && s.insights.confidenceScore < 70
  );
  const priceIncreases = subscriptions.filter(s => s.insights?.priceChangeDetected).length;
  
  const potentialSavingsCents = mutedSubscriptions.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0);
  const averageSubscriptionCents = activeSubscriptions.length > 0 ? 
    totalMonthlyCents / activeSubscriptions.length : 0;
  
  return {
    totalMonthlyCents,
    totalAnnualCents,
    subscriptionCount: subscriptions.length,
    activeSubscriptionCount: activeSubscriptions.length,
    categoryBreakdown,
    frequencyBreakdown,
    sourceBreakdown,
    insights: {
      potentialSavingsCents,
      unusedSubscriptions: mutedSubscriptions.length,
      priceIncreases,
      averageSubscriptionCents
    }
  };
}

function calculateNextDueDate(lastDate: string, frequency: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY'): string {
  const last = new Date(lastDate);
  const next = new Date(last);
  
  switch (frequency) {
    case 'WEEKLY':
      next.setDate(last.getDate() + 7);
      break;
    case 'BIWEEKLY':
      next.setDate(last.getDate() + 14);
      break;
    case 'MONTHLY':
      next.setMonth(last.getMonth() + 1);
      break;
    case 'QUARTERLY':
      next.setMonth(last.getMonth() + 3);
      break;
    case 'ANNUALLY':
      next.setFullYear(last.getFullYear() + 1);
      break;
  }
  
  return next.toISOString().split('T')[0];
}

export function filterSubscriptions(
  subscriptions: UnifiedSubscription[],
  filter: Partial<{
    search: string;
    source: 'plaid' | 'manual' | 'all';
    isActive: boolean;
    frequency: string;
    minAmountCents: number;
    maxAmountCents: number;
    categoryId: string;
    accountId: string;
    isMuted: boolean;
    isLinked: boolean;
  }>
): UnifiedSubscription[] {
  return subscriptions.filter(subscription => {
    // Search filter
    if (filter.search) {
      const searchLower = filter.search.toLowerCase();
      const matchesSearch = 
        subscription.name.toLowerCase().includes(searchLower) ||
        subscription.description.toLowerCase().includes(searchLower) ||
        subscription.merchantName?.toLowerCase().includes(searchLower) ||
        subscription.categoryName?.toLowerCase().includes(searchLower);
      
      if (!matchesSearch) return false;
    }
    
    // Source filter
    if (filter.source && filter.source !== 'all' && subscription.source !== filter.source) {
      return false;
    }
    
    // Active filter
    if (filter.isActive !== undefined && subscription.isActive !== filter.isActive) {
      return false;
    }
    
    // Frequency filter
    if (filter.frequency && subscription.frequency !== filter.frequency) {
      return false;
    }
    
    // Amount filters
    if (filter.minAmountCents !== undefined && subscription.monthlyEstimatedCents < filter.minAmountCents) {
      return false;
    }
    if (filter.maxAmountCents !== undefined && subscription.monthlyEstimatedCents > filter.maxAmountCents) {
      return false;
    }
    
    // Category filter
    if (filter.categoryId && subscription.categoryId !== filter.categoryId) {
      return false;
    }
    
    // Account filter
    if (filter.accountId && subscription.accountId !== filter.accountId) {
      return false;
    }
    
    // Muted filter
    if (filter.isMuted !== undefined && subscription.isMuted !== filter.isMuted) {
      return false;
    }
    
    // Linked filter
    if (filter.isLinked !== undefined && subscription.isLinked !== filter.isLinked) {
      return false;
    }
    
    return true;
  });
}