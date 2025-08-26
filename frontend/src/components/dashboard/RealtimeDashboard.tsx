// frontend/src/components/dashboard/RealtimeDashboard.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { 
  TrendingUp, 
  DollarSign, 
  Target, 
  CreditCard,
  AlertCircle
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { MetricCard } from '../ui/MetricCard';
import { ErrorState } from '../ui/ErrorState';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  useRealtimeTransactions,
  useNotifications,
  useUnreadNotificationsCount,
  useBudgetAlerts,
  useConnectionStatus,
} from '../../stores/realtimeStore';
import { useAuthUser } from '../../stores/authStore';
import { CurrencyUtils, formatCurrency, getTimeBasedGreeting } from '../../utils';
import { getRelativeTime } from '../../utils/date';
import RealtimeTransactionFeed from './RealtimeTransactionFeed';
import { NotificationPanel } from './NotificationPanel';
// Removed: import type { BudgetAlert } from '../../types/realtime';
import { DashboardFilters } from './DashboardFilters';
import { CategoryPieChart } from './CategoryPieChart';
import { TransactionHistogram } from './TransactionHistogram';
import type { DashboardFilters as FilterType, CategoryBreakdown, TransactionHistogramData } from '../../services/dashboardService';
import { dashboardService } from '../../services/dashboardService';
import { PlaidConnectionCard } from './PlaidConnectionCard';
import { useAccounts } from '../../hooks/useAccounts';
import { transactionService } from '../../services/transactionService';
import { NotificationService } from '../../services/notificationService';
import { useRealtimeStore } from '../../stores/realtimeStore';
import { invalidateDashboard } from '../../services/queryClient';


// Connection widget removed per request

export const RealtimeDashboard: React.FC = () => {
  // Isolation switches (set VITE_ENABLE_REALTIME or VITE_ENABLE_DASHBOARD_FETCH to 'false' to disable)
  const ENABLE_REALTIME = import.meta.env.VITE_ENABLE_REALTIME !== 'false';
  const ENABLE_DASHBOARD_FETCH = import.meta.env.VITE_ENABLE_DASHBOARD_FETCH !== 'false';
  // Filter state - default to last 30 days
  const [filters, setFilters] = useState<FilterType>(() => ({
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
  }));

  // React Query: dashboard summary and category breakdown
  const {
    data: summary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
    error: summaryError,
    refetch: refetchSummary
  } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardService.getDashboardSummary(),
    enabled: ENABLE_DASHBOARD_FETCH,
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: breakdown,
    isLoading: isBreakdownLoading,
    isError: isBreakdownError,
    error: breakdownError,
    refetch: refetchBreakdown
  } = useQuery({
    queryKey: ['category-breakdown', filters],
    queryFn: async () => {
      console.log('[DEBUG Dashboard] Fetching category breakdown with filters:', filters);
      const result = await dashboardService.getCategoryBreakdown(filters);
      console.log('[DEBUG Dashboard] Category breakdown result:', result);
      console.log('[DEBUG Dashboard] Expense items:', result?.filter((item: any) => item.total_amount < 0));
      return result;
    },
    enabled: ENABLE_DASHBOARD_FETCH && !!filters.start_date && !!filters.end_date,
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: histogramData,
    isLoading: isHistogramLoading,
    isError: isHistogramError,
    error: histogramError,
    refetch: refetchHistogram
  } = useQuery({
    queryKey: ['transaction-histogram', filters],
    queryFn: async () => {
      console.log('[DEBUG Dashboard] Fetching histogram data with filters:', filters);
      const result = await transactionService.getTransactionHistogram({
        start_date: filters.start_date,
        end_date: filters.end_date,
        category_id: filters.category_id,
        account_id: filters.account_id,
        bins: 10
      });
      console.log('[DEBUG Dashboard] Histogram result:', result);
      return result as TransactionHistogramData;
    },
    enabled: ENABLE_DASHBOARD_FETCH && !!filters.start_date && !!filters.end_date,
    staleTime: 5 * 60 * 1000,
  });

  // Transaction count derived from category breakdown data for consistency
  const transactionCountFromBreakdown = React.useMemo(() => {
    if (!breakdown || !Array.isArray(breakdown)) return 0;
    return breakdown.reduce((sum, item) => sum + (item.transaction_count || 0), 0);
  }, [breakdown]);
  
  // Real-time data (still useful for live updates)
  const realtimeTransactions = useRealtimeTransactions();
  const notifications = useNotifications();
  const unreadCount = useUnreadNotificationsCount();
  const budgetAlerts = useBudgetAlerts();
  const connection = useConnectionStatus();
  // Derive lightweight stats locally to avoid equality pitfalls
  const transactionCount = realtimeTransactions.length;
  const newTransactionCount = realtimeTransactions.filter((t) => t.isNew).length;
  // const transactionUpdates = useRealtimeStore((s) => s.transactionUpdates);
  const notificationCount = notifications.length;
  const queryClient = useQueryClient();
  
  // User data for personalized greeting
  const user = useAuthUser();
  
  // Accounts data for connection card
  const { refetch: refetchAccounts } = useAccounts();
  
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [updatingStats, setUpdatingStats] = useState<Record<string, boolean>>({});

  // Simple hydration setters from the store
  const setRecentTransactions = useRealtimeStore((s) => s.setRecentTransactions);
  const setNotifications = useRealtimeStore((s) => s.setNotifications);

  // Hydrate recent transactions and notifications on first load
  useEffect(() => {
    let cancelled = false;
    const hydrate = async () => {
      try {
        // Only hydrate if empty to avoid overwriting realtime items
        if (realtimeTransactions.length === 0) {
          const txs = await transactionService.getRecentTransactions(20);
          const mapped = txs.map((t: any) => ({
            id: t.id,
            userId: t.userId || t.user_id || '',
            accountId: t.accountId || t.account_id,
            categoryId: t.categoryId || t.category_id,
            amountCents: t.amountCents ?? t.amount_cents ?? 0,
            currency: t.currency || 'USD',
            description: t.description || '',
            merchant: t.merchant,
            transactionDate: (t.transactionDate || t.transaction_date) as string,
            // recurring/subscriptions removed
            createdAt: (t.createdAt || t.created_at || (t.transactionDate ? new Date(t.transactionDate).toISOString() : undefined)) as string,
            updatedAt: (t.updatedAt || t.updated_at || undefined) as string,
            // Required camelCase fields for Transaction
            accountName: t.accountName || t.account_name || '',
            categoryName: t.categoryName || t.category_name || undefined,
            // Realtime-only extras
            isNew: false,
            is_income: (t.amountCents ?? t.amount_cents ?? 0) > 0,
            category_name: t.categoryName || t.category_name,
            account_name: t.accountName || t.account_name,
          }));
          if (!cancelled) setRecentTransactions(mapped);
        }

        if (notifications.length === 0) {
          const resp = await NotificationService.getNotifications({ limit: 20 });
          const mappedNotifs = resp.notifications.map((n) => ({
            id: n.id,
            type: n.type,
            title: n.title,
            message: n.message,
            action_url: n.action_url,
            created_at: n.created_at,
            read: n.is_read,
            isNew: false,
          }));
          if (!cancelled) setNotifications(mappedNotifs);
        }
      } catch (e) {
        // Non-fatal: keep UI running even if hydration fails
        console.warn('Dashboard hydration failed:', e);
      }
    };
    hydrate();
    return () => { cancelled = true; };
    // Only run on mount; rely on realtime for updates afterwards
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle filter changes
  const handleFiltersChange = React.useCallback((newFilters: FilterType) => {
    setFilters(prev => (
      prev.start_date === newFilters.start_date && prev.end_date === newFilters.end_date
        ? prev
        : { ...prev, ...newFilters }
    ));
  }, []);

  // Update timestamp and stat animation when data changes
  useEffect(() => {
    if (!isSummaryLoading && !isBreakdownLoading && !isHistogramLoading && (summary || breakdown || histogramData)) {
      setLastUpdate(new Date());
      setUpdatingStats({ balance: true, spending: true, income: true, budget: true });
      const id = setTimeout(() => setUpdatingStats({}), 1000);
      return () => clearTimeout(id);
    }
  }, [isSummaryLoading, isBreakdownLoading, isHistogramLoading, summary, breakdown, histogramData]);

  const handleRefresh = useCallback(() => {
    invalidateDashboard();
    queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    queryClient.invalidateQueries({ predicate: (q) => Array.isArray(q.queryKey) && q.queryKey[0] === 'category-breakdown' });
    queryClient.invalidateQueries({ predicate: (q) => Array.isArray(q.queryKey) && q.queryKey[0] === 'transaction-histogram' });
    queryClient.invalidateQueries({ queryKey: ['accounts'] });
    setLastUpdate(new Date());
  }, [queryClient]);

  const handlePlaidSuccess = useCallback(() => {
    refetchAccounts();
    handleRefresh();
  }, [refetchAccounts, handleRefresh]);

  // Consolidated loading and error state flags
  const isLoading = isSummaryLoading || isBreakdownLoading || isHistogramLoading;
  const isError = isSummaryError || isBreakdownError || isHistogramError;
  const error = (summaryError as any) || (breakdownError as any) || (histogramError as any);

  // Calculate stats from dashboard data with proper fallbacks
  // Derive totals from category breakdown (expenses negative; income positive)
  const breakdownData = (breakdown || []) as CategoryBreakdown[];
  const totals = React.useMemo(() => {
    const income = breakdownData.filter(b => b.total_amount > 0).reduce((s, b) => s + b.total_amount, 0);
    const expensesAbs = breakdownData.filter(b => b.total_amount < 0).reduce((s, b) => s + Math.abs(b.total_amount), 0);
    const txnCount = breakdownData.reduce((s, b) => s + (b.transaction_count || 0), 0);
    return { income, expensesAbs, txnCount };
  }, [breakdownData]);

  const totalIncome = totals.income || 0;
  const totalExpenses = totals.expensesAbs || 0;
  const netAmount = totalIncome - totalExpenses;
  const summaryTransactionCount = totals.txnCount || 0;
  // Use consistent transaction count from breakdown data
  const periodTransactionCount = transactionCountFromBreakdown || summaryTransactionCount;
  
  // Data consistency validation
  const dataConsistencyCheck = React.useMemo(() => {
    const issues: string[] = [];
    
    if (Math.abs(transactionCountFromBreakdown - summaryTransactionCount) > 0 && summaryTransactionCount > 0) {
      issues.push(`Transaction count mismatch: breakdown=${transactionCountFromBreakdown}, totals=${summaryTransactionCount}`);
    }
    
    if (breakdownData.length > 0 && totalIncome === 0 && totalExpenses === 0) {
      issues.push('Category breakdown exists but totals are zero');
    }
    
    return {
      hasIssues: issues.length > 0,
      issues,
      summary: {
        fromBreakdown: transactionCountFromBreakdown,
        fromTotals: summaryTransactionCount,
        final: periodTransactionCount,
        totalIncome,
        totalExpenses,
        categoriesCount: breakdownData.length,
        filters
      }
    };
  }, [transactionCountFromBreakdown, summaryTransactionCount, periodTransactionCount, totalIncome, totalExpenses, breakdownData, filters]);
  
  console.log('[DEBUG Dashboard] Data consistency check:', dataConsistencyCheck);
  
  // Log warnings for potential issues
  if (dataConsistencyCheck.hasIssues) {
    console.warn('🚨 Dashboard data consistency issues detected:', dataConsistencyCheck.issues);
  }

  const dashboardStats = [
    {
      id: 'income',
      title: 'Total Income',
      // totalIncome/totalExpenses/netAmount are in dollars from the API, convert to cents for formatting
      value: CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(totalIncome)),
      change: `${periodTransactionCount} transactions`,
      changeType: 'positive' as const,
      iconComponent: TrendingUp,
      theme: 'income' as const,
    },
    {
      id: 'expenses',
      title: 'Total Expenses',
      value: CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(totalExpenses)),
      change: `Period expenses`,
      changeType: 'negative' as const,
      iconComponent: CreditCard,
      theme: 'expense' as const,
    },
    {
      id: 'net',
      title: 'Net Amount',
      value: CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(netAmount)),
      change: netAmount >= 0 ? 'Positive balance' : 'Negative balance',
      changeType: netAmount >= 0 ? ('positive' as const) : ('negative' as const),
      iconComponent: DollarSign,
      theme: netAmount >= 0 ? ('success' as const) : ('expense' as const),
    },
    {
      id: 'transactions',
      title: 'Transactions',
      value: String(periodTransactionCount),
      change: `In selected period`,
      changeType: 'neutral' as const,
      iconComponent: Target,
      theme: 'savings' as const,
    },
  ];

  if (isLoading) {
    // Lightweight skeletons for cards and chart
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" role="generic" />
          ))}
        </div>
        <div className="h-80 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" role="generic" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <ErrorState
            message="Failed to load dashboard data"
            error={error}
            onRetry={() => {
              refetchSummary();
              refetchBreakdown();
              refetchHistogram();
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Title for accessibility and tests */}
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xl font-bold text-gray-900">
            {getTimeBasedGreeting()}, {user?.displayName || 'there'}!
          </div>
          <div className="flex items-center space-x-4 mt-2">
            <p className="text-gray-600">
              Real-time financial overview
            </p>
            {connection.status !== 'connected' && (
              <span className="text-xs px-2 py-1 rounded bg-yellow-100 text-yellow-800">
                Realtime {connection.status} — showing latest snapshot
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="text-sm text-gray-500">
            Last updated: {getRelativeTime(lastUpdate.toISOString())}
          </div>
          <Button variant="outline" onClick={handleRefresh}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Dashboard Filters */}
      <DashboardFilters 
        filters={filters} 
        onFiltersChange={handleFiltersChange} 
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {dashboardStats.map((stat) => (
          <MetricCard
            key={stat.id}
            {...stat}
            variant="compact"
            isUpdating={updatingStats[stat.id]}
          />
        ))}
      </div>

      {/* Development Warning for Data Inconsistencies */}
      {import.meta.env.DEV && dataConsistencyCheck.hasIssues && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-yellow-400" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700 dark:text-yellow-200">
                <strong>Development Warning:</strong> Data inconsistency detected
              </p>
              <ul className="mt-2 text-xs text-yellow-600 dark:text-yellow-300 list-disc list-inside">
                {dataConsistencyCheck.issues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Money Flow Sankey Diagram - Removed (not implemented) */}

      {/* Spending Heatmap - Removed */}

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CategoryPieChart 
          data={(breakdown || []) as CategoryBreakdown[]} 
          title="Top Spending by Category" 
        />
        <TransactionHistogram 
          data={histogramData || null}
          title="Transaction Amount Distribution"
          isLoading={isHistogramLoading}
        />
      </div>

      {/* Active Alerts */}
      {budgetAlerts.length > 0 && (
        <Card className="border-l-4 border-l-yellow-400">
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertCircle className="h-5 w-5 text-yellow-500 mr-2" />
              Active Budget Alerts ({budgetAlerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {budgetAlerts.slice(0, 3).map((alert, index: number) => (
                <div key={index} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                  <div>
                    <div className="font-medium text-yellow-800">{alert.category || 'Budget Alert'}</div>
                    <div className="text-sm text-yellow-600">{alert.message}</div>
                  </div>
                  <div className="text-right">
                    {typeof (alert as any).spent_cents === 'number' && typeof (alert as any).amount_cents === 'number' ? (
                      <div className="font-bold text-yellow-800">
                        {formatCurrency((alert as any).spent_cents)} / {formatCurrency((alert as any).amount_cents)}
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bank Account Management Card - Always visible */}
      <PlaidConnectionCard onSuccess={handlePlaidSuccess} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Real-time Transaction Feed */}
        <div>
          <RealtimeTransactionFeed 
            transactions={ENABLE_REALTIME ? realtimeTransactions : []} 
            newCount={ENABLE_REALTIME ? newTransactionCount : 0}
            isLive={ENABLE_REALTIME && connection.status === 'connected'}
            totalCount={ENABLE_REALTIME ? transactionCount : 0}
          />
        </div>

        {/* Notifications Panel - show if notifications exist or if realtime is disabled */}
        {(notifications.length > 0 || !ENABLE_REALTIME) && (
          <div>
            <NotificationPanel 
              notifications={ENABLE_REALTIME ? notifications : []}
              unreadCount={ENABLE_REALTIME ? unreadCount : 0}
              isRealtimeEnabled={ENABLE_REALTIME}
            />
          </div>
        )}
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">New Transactions</div>
                <div className="text-2xl font-bold">
                  {ENABLE_REALTIME ? newTransactionCount : '—'}
                </div>
                {!ENABLE_REALTIME && (
                  <div className="text-xs text-gray-500">Realtime disabled</div>
                )}
              </div>
              <Target className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">Recent Activity</div>
                <div className="text-2xl font-bold">
                  {ENABLE_REALTIME ? realtimeTransactions.length : '—'}
                </div>
                <div className="text-xs text-gray-500">
                  {ENABLE_REALTIME ? 'Transactions in feed' : 'Realtime disabled'}
                </div>
              </div>
              {ENABLE_REALTIME ? (
                connection.status === 'connected' ? (
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
                    <span className="text-sm text-green-600">Live</span>
                  </div>
                ) : (
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-gray-500 rounded-full mr-2"></div>
                    <span className="text-sm text-gray-500">Offline</span>
                  </div>
                )
              ) : (
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></div>
                  <span className="text-sm text-yellow-600">Disabled</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">Notifications</div>
                <div className="text-2xl font-bold">
                  {ENABLE_REALTIME ? notificationCount : '—'}
                </div>
                <div className="text-xs text-gray-500">
                  {ENABLE_REALTIME 
                    ? (unreadCount > 0 ? `${unreadCount} unread` : 'All read')
                    : 'Realtime disabled'
                  }
                </div>
              </div>
              <div className="relative">
                <AlertCircle className="h-8 w-8 text-gray-400" />
                {ENABLE_REALTIME && unreadCount > 0 && (
                  <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <span className="text-xs text-white font-medium">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
