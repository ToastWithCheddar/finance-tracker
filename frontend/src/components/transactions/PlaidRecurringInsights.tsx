import React from 'react';
import { TrendingUp, DollarSign, Calendar, Building, PieChart } from 'lucide-react';
import { formatCurrency } from '../../utils/currency';
import type { PlaidRecurringInsights } from '../../types/plaidRecurring';

interface PlaidRecurringInsightsProps {
  insights: PlaidRecurringInsights;
}

export const PlaidRecurringInsights: React.FC<PlaidRecurringInsightsProps> = ({ insights }) => {
  const {
    total_subscriptions,
    active_subscriptions,
    muted_subscriptions,
    linked_subscriptions,
    total_monthly_cost_cents,
    total_monthly_cost_dollars,
    frequency_breakdown,
    status_breakdown,
    top_subscriptions,
    cost_by_account
  } = insights;

  return (
    <div className="space-y-6">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <TrendingUp className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">{total_subscriptions}</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Total Subscriptions</p>
            </div>
          </div>
        </div>

        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <Calendar className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">{active_subscriptions}</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Active</p>
            </div>
          </div>
        </div>

        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
              <DollarSign className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">
                {formatCurrency(total_monthly_cost_dollars)}
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Monthly Cost</p>
            </div>
          </div>
        </div>

        <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <Building className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">{linked_subscriptions}</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Linked to Rules</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Frequency Breakdown */}
        <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
            <PieChart className="h-5 w-5 mr-2" />
            Frequency Breakdown
          </h3>
          <div className="space-y-3">
            {Object.entries(frequency_breakdown).map(([frequency, count]) => (
              <div key={frequency} className="flex items-center justify-between">
                <span className="text-[hsl(var(--text))] capitalize">{frequency.toLowerCase()}</span>
                <div className="flex items-center">
                  <div className="w-24 bg-[hsl(var(--border))] rounded-full h-2 mr-3">
                    <div 
                      className="bg-blue-500 h-2 rounded-full" 
                      style={{ 
                        width: `${total_subscriptions > 0 ? (count / total_subscriptions) * 100 : 0}%` 
                      }}
                    />
                  </div>
                  <span className="text-sm font-medium text-[hsl(var(--text))] w-8 text-right">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Status Breakdown */}
        <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
            <TrendingUp className="h-5 w-5 mr-2" />
            Status Breakdown
          </h3>
          <div className="space-y-3">
            {Object.entries(status_breakdown).map(([status, count]) => {
              const statusColors = {
                'MATURE': 'bg-green-500',
                'EARLY_DETECTION': 'bg-yellow-500',
                'INACCURATE': 'bg-red-500',
                'TERMINATED': 'bg-gray-500'
              };
              const colorClass = statusColors[status as keyof typeof statusColors] || 'bg-gray-500';
              
              return (
                <div key={status} className="flex items-center justify-between">
                  <span className="text-[hsl(var(--text))] capitalize">
                    {status.toLowerCase().replace('_', ' ')}
                  </span>
                  <div className="flex items-center">
                    <div className="w-24 bg-[hsl(var(--border))] rounded-full h-2 mr-3">
                      <div 
                        className={`${colorClass} h-2 rounded-full`}
                        style={{ 
                          width: `${total_subscriptions > 0 ? (count / total_subscriptions) * 100 : 0}%` 
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-[hsl(var(--text))] w-8 text-right">{count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top Subscriptions */}
      {top_subscriptions.length > 0 && (
        <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
            <DollarSign className="h-5 w-5 mr-2" />
            Highest Cost Subscriptions
          </h3>
          <div className="space-y-3">
            {top_subscriptions.slice(0, 5).map((subscription, index) => (
              <div key={subscription.plaid_recurring_transaction_id} className="flex items-center justify-between p-3 bg-[hsl(var(--bg))] rounded-lg">
                <div className="flex items-center">
                  <div className="w-8 h-8 bg-[hsl(var(--brand))] text-white rounded-full flex items-center justify-center text-sm font-medium mr-3">
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium text-[hsl(var(--text))]">
                      {subscription.merchant_name || subscription.description}
                    </p>
                    <p className="text-sm text-[hsl(var(--text))] opacity-70 capitalize">
                      {subscription.frequency.toLowerCase()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-[hsl(var(--text))]">
                    {formatCurrency(subscription.monthly_estimated_amount_cents / 100)}
                  </p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">per month</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cost by Account */}
      {cost_by_account.length > 0 && (
        <div className="bg-[hsl(var(--surface))] p-6 rounded-lg border border-[hsl(var(--border))]">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
            <Building className="h-5 w-5 mr-2" />
            Cost by Account
          </h3>
          <div className="space-y-3">
            {cost_by_account.map((account) => (
              <div key={account.account_id} className="flex items-center justify-between p-3 bg-[hsl(var(--bg))] rounded-lg">
                <div>
                  <p className="font-medium text-[hsl(var(--text))]">{account.account_name}</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">
                    {account.subscription_count} subscription{account.subscription_count !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-[hsl(var(--text))]">
                    {formatCurrency(account.total_monthly_cents / 100)}
                  </p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">per month</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};