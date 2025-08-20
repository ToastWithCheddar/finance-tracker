import React from 'react';
import { 
  DollarSign, 
  TrendingUp, 
  Calendar, 
  AlertTriangle,
  Activity,
  Target,
  Users,
  PieChart
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { MetricCard } from '../ui';
import { formatCurrency } from '../../utils/currency';
import { CHART_COLORS } from '../../utils/categoryColors';
import type { SubscriptionAnalytics } from '../../types/subscription';

interface SubscriptionAnalyticsDashboardProps {
  analytics: SubscriptionAnalytics;
  isLoading?: boolean;
}


const CategoryBreakdownCard: React.FC<{ analytics: SubscriptionAnalytics }> = ({ analytics }) => (
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center">
        <PieChart className="h-5 w-5 text-blue-500 mr-2" />
        Spending by Category
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        {analytics.categoryBreakdown.slice(0, 6).map((category, index) => {
          const colorStyle = { backgroundColor: CHART_COLORS[index % CHART_COLORS.length] };
          
          return (
            <div key={category.categoryId} className="flex items-center justify-between">
              <div className="flex items-center space-x-3 flex-1">
                <div className="w-3 h-3 rounded-full" style={colorStyle} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[hsl(var(--text))] truncate">
                    {category.categoryName}
                  </p>
                  <p className="text-xs text-[hsl(var(--text))] opacity-60">
                    {category.count} subscription{category.count !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-[hsl(var(--text))]">
                  {formatCurrency(category.amountCents / 100)}
                </p>
                <p className="text-xs text-[hsl(var(--text))] opacity-60">
                  {category.percentage.toFixed(1)}%
                </p>
              </div>
            </div>
          );
        })}
        
        {analytics.categoryBreakdown.length > 6 && (
          <div className="pt-2 border-t border-[hsl(var(--border))]">
            <p className="text-xs text-[hsl(var(--text))] opacity-60 text-center">
              +{analytics.categoryBreakdown.length - 6} more categories
            </p>
          </div>
        )}
      </div>
    </CardContent>
  </Card>
);

const FrequencyBreakdownCard: React.FC<{ analytics: SubscriptionAnalytics }> = ({ analytics }) => (
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center">
        <Calendar className="h-5 w-5 text-green-500 mr-2" />
        Payment Frequency
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        {Object.entries(analytics.frequencyBreakdown)
          .sort(([,a], [,b]) => b.totalCents - a.totalCents)
          .map(([frequency, data]) => {
            const percentage = analytics.totalMonthlyCents > 0 
              ? (data.totalCents / analytics.totalMonthlyCents) * 100 
              : 0;
            
            return (
              <div key={frequency} className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-[hsl(var(--text))] capitalize">
                    {frequency.toLowerCase()}
                  </p>
                  <p className="text-xs text-[hsl(var(--text))] opacity-60">
                    {data.count} subscription{data.count !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-[hsl(var(--text))]">
                    {formatCurrency(data.totalCents / 100)}
                  </p>
                  <p className="text-xs text-[hsl(var(--text))] opacity-60">
                    {percentage.toFixed(1)}%
                  </p>
                </div>
              </div>
            );
          })}
      </div>
    </CardContent>
  </Card>
);

const SourceBreakdownCard: React.FC<{ analytics: SubscriptionAnalytics }> = ({ analytics }) => (
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center">
        <Users className="h-5 w-5 text-purple-500 mr-2" />
        Data Sources
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div>
            <p className="text-sm font-medium text-[hsl(var(--text))]">
              Plaid Detected
            </p>
            <p className="text-xs text-[hsl(var(--text))] opacity-60">
              {analytics.sourceBreakdown.plaid.count} subscription{analytics.sourceBreakdown.plaid.count !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-[hsl(var(--text))]">
              {formatCurrency(analytics.sourceBreakdown.plaid.totalCents / 100)}
            </p>
            <p className="text-xs text-[hsl(var(--text))] opacity-60">
              /month
            </p>
          </div>
        </div>
        
        <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div>
            <p className="text-sm font-medium text-[hsl(var(--text))]">
              Manual Rules
            </p>
            <p className="text-xs text-[hsl(var(--text))] opacity-60">
              {analytics.sourceBreakdown.manual.count} subscription{analytics.sourceBreakdown.manual.count !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-[hsl(var(--text))]">
              {formatCurrency(analytics.sourceBreakdown.manual.totalCents / 100)}
            </p>
            <p className="text-xs text-[hsl(var(--text))] opacity-60">
              /month
            </p>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

/**
 * Dashboard component that displays subscription analytics with metric cards,
 * insights, and breakdown visualizations. Provides a comprehensive overview
 * of subscription spending patterns and key metrics.
 */
export const SubscriptionAnalyticsDashboard: React.FC<SubscriptionAnalyticsDashboardProps> = ({ 
  analytics, 
  isLoading = false 
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="animate-pulse">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
                    <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  </div>
                  <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Main Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Monthly Total"
          value={formatCurrency(analytics.totalMonthlyCents / 100)}
          subtitle="Estimated monthly cost"
          icon={<DollarSign className="h-6 w-6" />}
        />
        
        <MetricCard
          title="Annual Total"
          value={formatCurrency(analytics.totalAnnualCents / 100)}
          subtitle="Estimated annual cost"
          icon={<TrendingUp className="h-6 w-6" />}
        />
        
        <MetricCard
          title="Active Subscriptions"
          value={analytics.activeSubscriptionCount.toString()}
          subtitle={`of ${analytics.subscriptionCount} total`}
          icon={<Activity className="h-6 w-6" />}
        />
        
        <MetricCard
          title="Average Cost"
          value={formatCurrency(analytics.insights.averageSubscriptionCents / 100)}
          subtitle="Per subscription/month"
          icon={<Target className="h-6 w-6" />}
        />
      </div>

      {/* Insights Cards */}
      {(analytics.insights.potentialSavingsCents > 0 || 
        analytics.insights.unusedSubscriptions > 0 || 
        analytics.insights.priceIncreases > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {analytics.insights.potentialSavingsCents > 0 && (
            <MetricCard
              title="Potential Savings"
              value={formatCurrency(analytics.insights.potentialSavingsCents / 100)}
              subtitle="From muted subscriptions"
              icon={<AlertTriangle className="h-6 w-6" />}
              className="border-orange-200 dark:border-orange-800"
            />
          )}
          
          {analytics.insights.unusedSubscriptions > 0 && (
            <MetricCard
              title="Unused Subscriptions"
              value={analytics.insights.unusedSubscriptions.toString()}
              subtitle="May need attention"
              icon={<AlertTriangle className="h-6 w-6" />}
              className="border-red-200 dark:border-red-800"
            />
          )}
          
          {analytics.insights.priceIncreases > 0 && (
            <MetricCard
              title="Price Changes"
              value={analytics.insights.priceIncreases.toString()}
              subtitle="Recent increases detected"
              icon={<TrendingUp className="h-6 w-6" />}
              className="border-yellow-200 dark:border-yellow-800"
            />
          )}
        </div>
      )}

      {/* Breakdown Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <CategoryBreakdownCard analytics={analytics} />
        <FrequencyBreakdownCard analytics={analytics} />
        <SourceBreakdownCard analytics={analytics} />
      </div>
    </div>
  );
};