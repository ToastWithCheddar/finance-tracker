import React, { useState } from 'react';
import { 
  AlertTriangle, 
  TrendingUp, 
  Users, 
  DollarSign,
  Eye,
  EyeOff,
  X,
  CheckCircle,
  AlertCircle,
  Info,
  Zap
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { formatCurrency } from '../../utils/currency';
import { useSubscriptionInsights } from '../../hooks/useUnifiedSubscriptions';
import type { UnifiedSubscription } from '../../types/subscription';

interface SubscriptionInsightsProps {
  subscriptions: UnifiedSubscription[];
}

interface InsightCardProps {
  type: 'low_usage' | 'price_increase' | 'duplicate' | 'potential_saving';
  title: string;
  description: string;
  subscriptions: UnifiedSubscription[];
  potentialSavingsCents?: number;
  severity: 'low' | 'medium' | 'high';
  onDismiss?: () => void;
  onAction?: () => void;
  actionLabel?: string;
}

const InsightCard: React.FC<InsightCardProps> = ({
  type,
  title,
  description,
  subscriptions,
  potentialSavingsCents,
  severity,
  onDismiss,
  onAction,
  actionLabel
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  const getIcon = () => {
    switch (type) {
      case 'low_usage':
        return <EyeOff className="h-5 w-5" />;
      case 'price_increase':
        return <TrendingUp className="h-5 w-5" />;
      case 'duplicate':
        return <Users className="h-5 w-5" />;
      case 'potential_saving':
        return <DollarSign className="h-5 w-5" />;
      default:
        return <Info className="h-5 w-5" />;
    }
  };

  const getColorClass = () => {
    switch (severity) {
      case 'high':
        return 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10';
      case 'medium':
        return 'border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/10';
      case 'low':
        return 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10';
      default:
        return 'border-gray-200 dark:border-gray-800';
    }
  };

  const getIconColorClass = () => {
    switch (severity) {
      case 'high':
        return 'text-red-600 dark:text-red-400';
      case 'medium':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'low':
        return 'text-blue-600 dark:text-blue-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  return (
    <Card className={`${getColorClass()} transition-all duration-200`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className={`mt-0.5 ${getIconColorClass()}`}>
              {getIcon()}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-[hsl(var(--text))] mb-1">
                  {title}
                </h4>
                <div className="flex items-center space-x-2">
                  {potentialSavingsCents && potentialSavingsCents > 0 && (
                    <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                      Save {formatCurrency(potentialSavingsCents / 100)}/mo
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="h-6 w-6 p-0"
                  >
                    {isExpanded ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDismiss}
                    className="h-6 w-6 p-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              
              <p className="text-sm text-[hsl(var(--text))] opacity-80 mb-2">
                {description}
              </p>

              {subscriptions.length > 0 && (
                <div className="flex items-center space-x-4 text-xs text-[hsl(var(--text))] opacity-60">
                  <span>{subscriptions.length} subscription{subscriptions.length !== 1 ? 's' : ''}</span>
                  <span>
                    {formatCurrency(
                      subscriptions.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0) / 100
                    )}/month
                  </span>
                </div>
              )}

              {isExpanded && subscriptions.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                  <div className="space-y-2">
                    {subscriptions.slice(0, 5).map(subscription => (
                      <div 
                        key={subscription.id} 
                        className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded border"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium text-[hsl(var(--text))]">
                            {subscription.name}
                          </p>
                          <p className="text-xs text-[hsl(var(--text))] opacity-60">
                            {subscription.frequency.toLowerCase()} • {subscription.source}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-[hsl(var(--text))]">
                            {formatCurrency(subscription.monthlyEstimatedCents / 100)}
                          </p>
                          <p className="text-xs text-[hsl(var(--text))] opacity-60">
                            /month
                          </p>
                        </div>
                      </div>
                    ))}
                    {subscriptions.length > 5 && (
                      <p className="text-xs text-[hsl(var(--text))] opacity-60 text-center pt-2">
                        +{subscriptions.length - 5} more subscriptions
                      </p>
                    )}
                  </div>
                </div>
              )}

              {actionLabel && onAction && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onAction}
                    className="text-xs"
                  >
                    <Zap className="h-3 w-3 mr-1" />
                    {actionLabel}
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const InsightsSummaryCard: React.FC<{ 
  totalInsights: number;
  potentialSavingsCents: number;
  onShowAll: () => void;
}> = ({ totalInsights, potentialSavingsCents, onShowAll }) => (
  <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white">
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold mb-2">Subscription Insights</h3>
          <p className="text-blue-100 mb-3">
            We found {totalInsights} insight{totalInsights !== 1 ? 's' : ''} to help optimize your subscriptions
          </p>
          {potentialSavingsCents > 0 && (
            <div className="flex items-center space-x-2">
              <DollarSign className="h-4 w-4" />
              <span className="font-semibold">
                Potential savings: {formatCurrency(potentialSavingsCents / 100)}/month
              </span>
            </div>
          )}
        </div>
        <div className="text-right">
          <Button
            variant="secondary"
            onClick={onShowAll}
            className="bg-white/20 hover:bg-white/30 text-white border-white/30"
          >
            View All
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
);

/**
 * Insights component that analyzes subscription data to provide actionable
 * recommendations such as identifying unused subscriptions, price increases,
 * duplicates, and potential savings opportunities.
 */
export const SubscriptionInsights: React.FC<SubscriptionInsightsProps> = ({ subscriptions }) => {
  const [showAllInsights, setShowAllInsights] = useState(false);
  const insights = useSubscriptionInsights(subscriptions);

  // Calculate potential savings from all insights
  const totalPotentialSavings = 
    insights.lowUsage.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0) +
    subscriptions.filter(s => s.isMuted).reduce((sum, s) => sum + s.monthlyEstimatedCents, 0);

  // Don't render if no insights
  if (insights.totalInsights === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-2">
            All Good!
          </h3>
          <p className="text-[hsl(var(--text))] opacity-70">
            No subscription optimization opportunities detected at this time.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <InsightsSummaryCard
        totalInsights={insights.totalInsights}
        potentialSavingsCents={totalPotentialSavings}
        onShowAll={() => setShowAllInsights(!showAllInsights)}
      />

      {/* High Priority Insights (Always Visible) */}
      {insights.lowUsage.length > 0 && (
        <InsightCard
          type="low_usage"
          title="Low Usage Detected"
          description="These subscriptions may not be providing value based on usage patterns."
          subscriptions={insights.lowUsage}
          potentialSavingsCents={insights.lowUsage.reduce((sum, s) => sum + s.monthlyEstimatedCents, 0)}
          severity="high"
          actionLabel="Review Usage"
          onAction={() => {
            // TODO: Implement low usage subscription review functionality
            // This should open a modal to review and potentially cancel unused subscriptions
          }}
        />
      )}

      {insights.priceIncreases.length > 0 && (
        <InsightCard
          type="price_increase"
          title="Price Increases Detected"
          description="These subscriptions have had recent price increases that you should review."
          subscriptions={insights.priceIncreases}
          severity="medium"
          actionLabel="Review Changes"
          onAction={() => {
            // TODO: Implement price increase review functionality  
            // This should open a modal to review and acknowledge price changes
          }}
        />
      )}

      {/* Show additional insights when expanded */}
      {showAllInsights && (
        <>
          {insights.duplicates.length > 0 && (
            insights.duplicates.map((duplicateGroup, index) => (
              <InsightCard
                key={`duplicate-${index}`}
                type="duplicate"
                title="Potential Duplicates"
                description="These subscriptions appear similar and might be duplicates."
                subscriptions={duplicateGroup}
                severity="medium"
                actionLabel="Review Duplicates"
                onAction={() => {
                  // TODO: Implement duplicate subscription review functionality
                  // This should open a modal to consolidate or remove duplicate subscriptions
                }}
              />
            ))
          )}

          {insights.lowConfidence.length > 0 && (
            <InsightCard
              type="potential_saving"
              title="Low Confidence Subscriptions"
              description="These subscriptions have low confidence scores and should be verified."
              subscriptions={insights.lowConfidence}
              severity="low"
              actionLabel="Verify Subscriptions"
              onAction={() => {
                // TODO: Implement low confidence subscription verification functionality
                // This should open a modal to manually verify or correct subscription details
              }}
            />
          )}
        </>
      )}

      {/* Show muted subscriptions as potential savings */}
      {subscriptions.filter(s => s.isMuted).length > 0 && (
        <InsightCard
          type="potential_saving"
          title="Muted Subscriptions"
          description="You have muted subscriptions that could be cancelled for immediate savings."
          subscriptions={subscriptions.filter(s => s.isMuted)}
          potentialSavingsCents={subscriptions.filter(s => s.isMuted).reduce((sum, s) => sum + s.monthlyEstimatedCents, 0)}
          severity="low"
          actionLabel="Review Muted"
          onAction={() => {
            // TODO: Implement muted subscription review functionality
            // This should open a modal to review and potentially unmute or cancel subscriptions
          }}
        />
      )}
    </div>
  );
};