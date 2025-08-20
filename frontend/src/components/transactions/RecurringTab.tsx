import React, { useState } from 'react';
import { RefreshCw, AlertCircle, Activity, TrendingUp } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { formatCurrency } from '../../utils/currency';
import { usePlaidRecurringTransactions, usePlaidRecurringInsights, usePlaidRecurringActions } from '../../hooks/usePlaidRecurring';
import { PlaidSubscriptionsList } from './PlaidSubscriptionsList';
import { PlaidRecurringInsights } from './PlaidRecurringInsights';
import { SubscriptionManager } from '../subscriptions/SubscriptionManager';
import type { 
  PlaidRecurringFilter,
  PlaidRecurringTransaction,
  PlaidRecurringInsights as PlaidInsightsType
} from '../../types/plaidRecurring';

export const RecurringTab: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'subscriptions' | 'insights'>('subscriptions');
  const [filter, setFilter] = useState<PlaidRecurringFilter>({
    stream_status: 'active',
    limit: 50
  });

  const {
    data: recurringData,
    loading: recurringLoading,
    error: recurringError,
    refetch: refetchRecurring
  } = usePlaidRecurringTransactions(filter);

  const {
    data: insights,
    loading: insightsLoading,
    error: insightsError,
    refetch: refetchInsights
  } = usePlaidRecurringInsights();

  const { refetchAll } = usePlaidRecurringActions();

  const handleRefresh = async () => {
    await refetchAll();
  };

  if (recurringError || insightsError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900">Error loading recurring transactions</h3>
          <p className="text-sm text-gray-500 mt-1">
            {recurringError || insightsError}
          </p>
          <Button onClick={handleRefresh} className="mt-4">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Recurring Transactions</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage your subscriptions and recurring payments detected by Plaid
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={recurringLoading || insightsLoading}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${(recurringLoading || insightsLoading) ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {insights && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Monthly</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(insights.totalMonthlyAmount)}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Subscriptions</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {insights.activeCount}
                  </p>
                </div>
                <Activity className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Avg. Payment</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(insights.averageAmount)}
                  </p>
                </div>
                <AlertCircle className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveSubTab('subscriptions')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeSubTab === 'subscriptions'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Subscriptions
          </button>
          <button
            onClick={() => setActiveSubTab('insights')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeSubTab === 'insights'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Insights
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeSubTab === 'subscriptions' && (
        <div className="space-y-6">
          {recurringLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <>
              <PlaidSubscriptionsList
                data={recurringData}
                onFilterChange={setFilter}
                currentFilter={filter}
              />
              <SubscriptionManager />
            </>
          )}
        </div>
      )}

      {activeSubTab === 'insights' && (
        <div className="space-y-6">
          {insightsLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <PlaidRecurringInsights insights={insights} />
          )}
        </div>
      )}
    </div>
  );
};

export default RecurringTab;