import { useMemo } from 'react';
import { usePlaidRecurringTransactions, usePlaidRecurringInsights } from './usePlaidRecurring';
import { useRecurringRules, useRecurringStats } from './useRecurring';
import { consolidateSubscriptions, calculateSubscriptionAnalytics, filterSubscriptions } from '../utils/subscriptionUtils';
import type { 
  UnifiedSubscription, 
  SubscriptionAnalytics, 
  UnifiedSubscriptionFilter 
} from '../types/subscription';
import type { PlaidRecurringFilter, RecurringRuleFilter } from '../types';

interface UseUnifiedSubscriptionsOptions {
  filters?: UnifiedSubscriptionFilter;
  enabled?: boolean;
}

interface UseUnifiedSubscriptionsReturn {
  subscriptions: UnifiedSubscription[];
  filteredSubscriptions: UnifiedSubscription[];
  analytics: SubscriptionAnalytics;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
  plaidData: {
    subscriptions: UnifiedSubscription[];
    insights: any;
    isLoading: boolean;
  };
  manualData: {
    subscriptions: UnifiedSubscription[];
    stats: any;
    isLoading: boolean;
  };
}

export const useUnifiedSubscriptions = (
  options: UseUnifiedSubscriptionsOptions = {}
): UseUnifiedSubscriptionsReturn => {
  const { filters, enabled = true } = options;

  // Extract filters for underlying data sources
  const plaidFilters: PlaidRecurringFilter = {
    include_muted: true, // We'll handle muting at the unified level
    ...filters?.plaidFilters
  };

  const ruleFilters: RecurringRuleFilter = {
    is_active: undefined, // We'll handle active filtering at the unified level
    ...filters?.ruleFilters
  };

  // Fetch Plaid recurring data
  const {
    data: plaidTransactions,
    isLoading: plaidLoading,
    error: plaidError,
    refetch: refetchPlaid
  } = usePlaidRecurringTransactions(plaidFilters, enabled);

  const {
    data: plaidInsights,
    isLoading: plaidInsightsLoading
  } = usePlaidRecurringInsights(enabled);

  // Fetch manual recurring rules data
  const {
    data: rulesData,
    isLoading: rulesLoading,
    error: rulesError,
    refetch: refetchRules
  } = useRecurringRules(1, 100, ruleFilters, enabled);

  const {
    data: recurringStats,
    isLoading: recurringStatsLoading
  } = useRecurringStats(enabled);

  // Consolidate data from both sources
  const allSubscriptions = useMemo(() => {
    if (!plaidTransactions || !rulesData?.items) {
      return [];
    }

    return consolidateSubscriptions(plaidTransactions, rulesData.items);
  }, [plaidTransactions, rulesData?.items]);

  // Apply unified filters
  const filteredSubscriptions = useMemo(() => {
    if (!filters) {
      return allSubscriptions;
    }

    return filterSubscriptions(allSubscriptions, {
      search: filters.search,
      source: filters.source,
      isActive: filters.isActive,
      frequency: filters.frequency,
      minAmountCents: filters.minAmountCents,
      maxAmountCents: filters.maxAmountCents,
      categoryId: filters.categoryId,
      accountId: filters.accountId,
      isMuted: filters.isMuted,
      isLinked: filters.isLinked
    });
  }, [allSubscriptions, filters]);

  // Calculate analytics for filtered subscriptions
  const analytics = useMemo(() => {
    return calculateSubscriptionAnalytics(filteredSubscriptions);
  }, [filteredSubscriptions]);

  // Split subscriptions by source for detailed views
  const plaidSubscriptions = useMemo(() => 
    allSubscriptions.filter(s => s.source === 'plaid'), 
    [allSubscriptions]
  );

  const manualSubscriptions = useMemo(() => 
    allSubscriptions.filter(s => s.source === 'manual'), 
    [allSubscriptions]
  );

  // Aggregate loading states
  const isLoading = plaidLoading || rulesLoading || plaidInsightsLoading || recurringStatsLoading;

  // Aggregate errors
  const error = plaidError || rulesError;

  // Combined refetch function
  const refetch = () => {
    refetchPlaid();
    refetchRules();
  };

  return {
    subscriptions: allSubscriptions,
    filteredSubscriptions,
    analytics,
    isLoading,
    error,
    refetch,
    plaidData: {
      subscriptions: plaidSubscriptions,
      insights: plaidInsights,
      isLoading: plaidLoading || plaidInsightsLoading
    },
    manualData: {
      subscriptions: manualSubscriptions,
      stats: recurringStats,
      isLoading: rulesLoading || recurringStatsLoading
    }
  };
};

// Hook for subscription actions that work across both sources
export const useUnifiedSubscriptionActions = () => {
  // Import action hooks from both sources
  const plaidActions = {
    // Will be implemented when integrating with existing action hooks
  };

  const manualActions = {
    // Will be implemented when integrating with existing action hooks
  };

  const handleMute = async (subscription: UnifiedSubscription, muted: boolean) => {
    if (subscription.source === 'plaid') {
      // Use plaid mute action
      console.log('Muting Plaid subscription:', subscription.sourceId, muted);
    } else {
      // Manual rules don't support muting, but we could deactivate them
      console.log('Manual rules do not support muting');
    }
  };

  const handleLink = async (plaidSubscription: UnifiedSubscription, manualSubscription: UnifiedSubscription) => {
    if (plaidSubscription.source !== 'plaid' || manualSubscription.source !== 'manual') {
      throw new Error('Invalid subscription types for linking');
    }
    
    console.log('Linking subscriptions:', plaidSubscription.sourceId, manualSubscription.sourceId);
  };

  const handleUnlink = async (subscription: UnifiedSubscription) => {
    if (subscription.source === 'plaid' && subscription.isLinked) {
      console.log('Unlinking Plaid subscription:', subscription.sourceId);
    }
  };

  const handleEdit = async (subscription: UnifiedSubscription, updates: any) => {
    if (subscription.source === 'manual') {
      console.log('Editing manual rule:', subscription.sourceId, updates);
    } else {
      console.log('Plaid subscriptions cannot be directly edited');
    }
  };

  const handleDelete = async (subscription: UnifiedSubscription) => {
    if (subscription.source === 'manual') {
      console.log('Deleting manual rule:', subscription.sourceId);
    } else {
      console.log('Plaid subscriptions cannot be deleted, only muted');
    }
  };

  return {
    mute: handleMute,
    link: handleLink,
    unlink: handleUnlink,
    edit: handleEdit,
    delete: handleDelete,
    isLoading: false // Will be updated when integrating with actual action hooks
  };
};

// Specialized hook for subscription insights
export const useSubscriptionInsights = (subscriptions: UnifiedSubscription[]) => {
  const insights = useMemo(() => {
    const lowUsageSubscriptions = subscriptions.filter(s => 
      s.insights?.isLowUsage || (s.insights?.usageScore && s.insights.usageScore < 30)
    );

    const priceIncreases = subscriptions.filter(s => 
      s.insights?.priceChangeDetected
    );

    const lowConfidenceSubscriptions = subscriptions.filter(s =>
      s.insights?.confidenceScore && s.insights.confidenceScore < 70
    );

    const duplicateCandidates = findPotentialDuplicates(subscriptions);

    return {
      lowUsage: lowUsageSubscriptions,
      priceIncreases,
      lowConfidence: lowConfidenceSubscriptions,
      duplicates: duplicateCandidates,
      totalInsights: lowUsageSubscriptions.length + priceIncreases.length + duplicateCandidates.length
    };
  }, [subscriptions]);

  return insights;
};

// Helper function to find potential duplicate subscriptions
function findPotentialDuplicates(subscriptions: UnifiedSubscription[]): UnifiedSubscription[][] {
  const duplicates: UnifiedSubscription[][] = [];
  const processed = new Set<string>();

  subscriptions.forEach((subscription, index) => {
    if (processed.has(subscription.id)) return;

    const similarSubscriptions = subscriptions.slice(index + 1).filter(other => {
      if (processed.has(other.id)) return false;

      // Check for similar names (fuzzy matching)
      const nameSimilarity = calculateStringSimilarity(
        subscription.name.toLowerCase(),
        other.name.toLowerCase()
      );

      // Check for similar amounts (within 10%)
      const amountDiff = Math.abs(subscription.monthlyEstimatedCents - other.monthlyEstimatedCents);
      const amountSimilarity = amountDiff / Math.max(subscription.monthlyEstimatedCents, other.monthlyEstimatedCents);

      return nameSimilarity > 0.7 || amountSimilarity < 0.1;
    });

    if (similarSubscriptions.length > 0) {
      const duplicateGroup = [subscription, ...similarSubscriptions];
      duplicates.push(duplicateGroup);
      
      // Mark all as processed
      duplicateGroup.forEach(sub => processed.add(sub.id));
    }
  });

  return duplicates;
}

// Simple string similarity calculation (Jaccard similarity)
function calculateStringSimilarity(str1: string, str2: string): number {
  const set1 = new Set(str1.split(''));
  const set2 = new Set(str2.split(''));
  
  const intersection = new Set([...set1].filter(x => set2.has(x)));
  const union = new Set([...set1, ...set2]);
  
  return intersection.size / union.size;
}