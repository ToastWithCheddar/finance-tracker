import React from 'react';
import { 
  TrendingUp, 
  Target, 
  Calendar, 
  BarChart3, 
  PieChart,
  Activity,
  AlertCircle
} from 'lucide-react';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useRuleEffectiveness } from '../../hooks/useCategorizationRules';
import type { 
  CategorizationRule,
  RuleEffectivenessMetrics as MetricsType
} from '../../types/categorizationRules';

interface RuleEffectivenessMetricsProps {
  selectedRule: CategorizationRule | null;
}

interface MetricsDisplayProps {
  metrics: MetricsType;
}

const MetricsDisplay: React.FC<MetricsDisplayProps> = ({ metrics }) => {
  const getSuccessRateColor = (rate: number) => {
    if (rate < 0.5) return 'text-red-600';
    if (rate < 0.8) return 'text-orange-600';
    return 'text-green-600';
  };

  return (
    <div className="space-y-6">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <Target className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">{metrics.times_applied}</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Times Applied</p>
            </div>
          </div>
        </div>

        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className={`text-2xl font-bold ${getSuccessRateColor(metrics.success_rate)}`}>
                {Math.round(metrics.success_rate * 100)}%
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Success Rate</p>
            </div>
          </div>
        </div>

        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <BarChart3 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">{metrics.total_transactions_affected}</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Transactions Affected</p>
            </div>
          </div>
        </div>

        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
              <Activity className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">
                {Math.round(metrics.avg_confidence_score * 100)}%
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Avg. Confidence</p>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Over Time */}
      {metrics.applications_by_month.length > 0 && (
        <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
            <Calendar className="h-5 w-5 mr-2" />
            Performance Over Time
          </h3>
          <div className="space-y-3">
            {metrics.applications_by_month.slice(-6).map((month) => (
              <div key={month.month} className="flex items-center justify-between">
                <span className="text-[hsl(var(--text))]">{month.month}</span>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <span className="text-sm font-medium text-[hsl(var(--text))]">
                      {month.applications} applications
                    </span>
                  </div>
                  <div className="w-32 bg-[hsl(var(--border))] rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${getSuccessRateColor(month.success_rate).replace('text-', 'bg-')}`}
                      style={{ width: `${month.success_rate * 100}%` }}
                    />
                  </div>
                  <span className={`text-sm font-medium ${getSuccessRateColor(month.success_rate)} w-12 text-right`}>
                    {Math.round(month.success_rate * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categories and Merchants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Common Categories Assigned */}
        {metrics.common_categories_assigned.length > 0 && (
          <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
            <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
              <PieChart className="h-5 w-5 mr-2" />
              Common Categories Assigned
            </h3>
            <div className="space-y-3">
              {metrics.common_categories_assigned.slice(0, 5).map((category, index) => (
                <div key={category.category_id} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-6 h-6 bg-[hsl(var(--brand))] text-white rounded-full flex items-center justify-center text-xs font-medium mr-3">
                      {index + 1}
                    </div>
                    <span className="text-[hsl(var(--text))]">{category.category_name}</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-20 bg-[hsl(var(--border))] rounded-full h-2 mr-3">
                      <div 
                        className="bg-blue-500 h-2 rounded-full" 
                        style={{ 
                          width: `${(category.count / metrics.total_transactions_affected) * 100}%` 
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-[hsl(var(--text))] w-8 text-right">
                      {category.count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Common Merchants Matched */}
        {metrics.common_merchants_matched.length > 0 && (
          <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
            <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
              <BarChart3 className="h-5 w-5 mr-2" />
              Common Merchants Matched
            </h3>
            <div className="space-y-3">
              {metrics.common_merchants_matched.slice(0, 5).map((merchant, index) => (
                <div key={merchant.merchant} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-6 h-6 bg-[hsl(var(--brand))] text-white rounded-full flex items-center justify-center text-xs font-medium mr-3">
                      {index + 1}
                    </div>
                    <span className="text-[hsl(var(--text))] truncate">{merchant.merchant}</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-20 bg-[hsl(var(--border))] rounded-full h-2 mr-3">
                      <div 
                        className="bg-green-500 h-2 rounded-full" 
                        style={{ 
                          width: `${(merchant.count / metrics.total_transactions_affected) * 100}%` 
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-[hsl(var(--text))] w-8 text-right">
                      {merchant.count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Rule Info */}
      <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
        <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4">Rule Information</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-lg font-bold text-[hsl(var(--text))]">{metrics.rule_name}</p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Rule Name</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[hsl(var(--text))]">
              {new Date(metrics.created_at).toLocaleDateString()}
            </p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Created</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[hsl(var(--text))]">
              {metrics.last_applied_at 
                ? new Date(metrics.last_applied_at).toLocaleDateString()
                : 'Never'
              }
            </p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Last Applied</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[hsl(var(--text))]">{metrics.rule_id.slice(0, 8)}...</p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Rule ID</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export const RuleEffectivenessMetrics: React.FC<RuleEffectivenessMetricsProps> = ({ 
  selectedRule 
}) => {
  const {
    data: metrics,
    isLoading,
    error
  } = useRuleEffectiveness(selectedRule?.id || '', !!selectedRule);

  if (!selectedRule) {
    return (
      <div className="text-center py-12">
        <Target className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
        <p className="text-[hsl(var(--text))] opacity-80">Select a rule to view metrics</p>
        <p className="text-sm text-[hsl(var(--text))] opacity-70">
          Click on a rule from the rules list to see its effectiveness metrics
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
        <p className="text-red-600 dark:text-red-400 mb-2">Failed to load metrics</p>
        <p className="text-sm text-[hsl(var(--text))] opacity-70">
          {error.message || 'Please try refreshing the page'}
        </p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="text-center py-12">
        <TrendingUp className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
        <p className="text-[hsl(var(--text))] opacity-80">No metrics available</p>
        <p className="text-sm text-[hsl(var(--text))] opacity-70">
          This rule hasn't been applied yet or metrics are not available
        </p>
      </div>
    );
  }

  return <MetricsDisplay metrics={metrics} />;
};