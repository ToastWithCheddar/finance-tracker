// frontend/src/components/dashboard/RealtimeDashboard.tsx
import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Target, 
  CreditCard,
  AlertCircle,
  Clock,
  Wifi,
  WifiOff
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useDashboardAnalytics, useSpendingTrends } from '../../hooks/useDashboard';
import { 
  useConnectionStatus, 
  useRealtimeTransactions,
  useNotifications,
  useUnreadNotificationsCount,
  useBudgetAlerts,
  useRealtimeStats
} from '../../stores/realtimeStore';
import { formatCurrency, formatRelativeTime } from '../../utils';
import RealtimeTransactionFeed from './RealtimeTransactionFeed';
import { NotificationPanel } from './NotificationPanel';
// Removed: import type { BudgetAlert } from '../../types/realtime';
import { DashboardFilters } from './DashboardFilters';
import { CategoryPieChart } from './CategoryPieChart';
import MonthlyComparisonChart from './MonthlyComparisonChart';
import { SankeyChart } from './SankeyChart';
import { SpendingHeatmap } from './SpendingHeatmap';
import type { DashboardFilters as FilterType } from '../../services/dashboardService';

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: React.ComponentType<{ className?: string; size?: number | string; }>;
  isLoading?: boolean;
  isUpdating?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  change, 
  changeType = 'neutral', 
  icon: Icon,
  isLoading = false,
  isUpdating = false
}) => {
  // Get themed colors based on card type
  const getCardTheme = () => {
    if (title.includes('Income')) {
      return {
        cardClass: 'bg-income-gradient border-income-200 shadow-lg shadow-income-100/50 dark:shadow-income-800/50',
        iconColor: 'text-income-600 dark:text-income-400',
        titleColor: 'text-income-700 dark:text-income-300',
        valueColor: 'text-income-900 dark:text-income-100',
        changeColor: 'text-income-600 dark:text-income-400',
      };
    } else if (title.includes('Expense')) {
      return {
        cardClass: 'bg-expense-gradient border-expense-200 shadow-lg shadow-expense-100/50 dark:shadow-expense-800/50',
        iconColor: 'text-expense-600 dark:text-expense-400',
        titleColor: 'text-expense-700 dark:text-expense-300',
        valueColor: 'text-expense-900 dark:text-expense-100',
        changeColor: 'text-expense-600 dark:text-expense-400',
      };
    } else if (title.includes('Net')) {
      const isPositive = changeType === 'positive';
      return {
        cardClass: isPositive 
          ? 'bg-success-gradient border-success-200 shadow-lg shadow-success-100/50 dark:shadow-success-800/50'
          : 'bg-expense-gradient border-expense-200 shadow-lg shadow-expense-100/50 dark:shadow-expense-800/50',
        iconColor: isPositive ? 'text-success-600 dark:text-success-400' : 'text-expense-600 dark:text-expense-400',
        titleColor: isPositive ? 'text-success-700 dark:text-success-300' : 'text-expense-700 dark:text-expense-300',
        valueColor: isPositive ? 'text-success-900 dark:text-success-100' : 'text-expense-900 dark:text-expense-100',
        changeColor: isPositive ? 'text-success-600 dark:text-success-400' : 'text-expense-600 dark:text-expense-400',
      };
    } else if (title.includes('Transaction')) {
      return {
        cardClass: 'bg-savings-gradient border-savings-200 shadow-lg shadow-savings-100/50 dark:shadow-savings-800/50',
        iconColor: 'text-savings-600 dark:text-savings-400',
        titleColor: 'text-savings-700 dark:text-savings-300',
        valueColor: 'text-savings-900 dark:text-savings-100',
        changeColor: 'text-savings-600 dark:text-savings-400',
      };
    } else {
      // Default theme
      return {
        cardClass: 'bg-gradient-to-br from-white to-gray-50 border-gray-200 shadow-lg dark:from-gray-800 dark:to-gray-700 dark:border-gray-600',
        iconColor: 'text-gray-500 dark:text-gray-400',
        titleColor: 'text-gray-600 dark:text-gray-400',
        valueColor: 'text-gray-900 dark:text-gray-100',
        changeColor: 'text-gray-600 dark:text-gray-400',
      };
    }
  };

  const theme = getCardTheme();
  const ChangeIcon = changeType === 'positive' ? TrendingUp : TrendingDown;

  return (
    <Card className={`
      ${theme.cardClass}
      card-hover
      transition-all duration-300 
      ${isUpdating ? 'ring-2 ring-blue-300 scale-105 glow-savings animate-bounce-gentle' : ''}
      backdrop-blur-sm
    `}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className={`text-sm font-medium ${theme.titleColor}`}>
          {title}
        </CardTitle>
        <div className="relative">
          <Icon className={`h-5 w-5 ${theme.iconColor} ${isUpdating ? 'animate-pulse' : ''}`} />
          {isUpdating && (
            <div className="absolute inset-0 animate-ping">
              <Icon className={`h-5 w-5 ${theme.iconColor} opacity-75`} />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className={`
          text-3xl font-bold transition-all duration-300 
          ${theme.valueColor}
          ${isLoading ? 'animate-pulse shimmer' : ''}
        `}>
          {isLoading ? '...' : value}
        </div>
        {change && (
          <div className={`flex items-center text-sm ${theme.changeColor} mt-2 font-medium`}>
            <ChangeIcon className="h-4 w-4 mr-1" />
            {change}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const ConnectionStatus: React.FC = () => {
  const connectionStatus = useConnectionStatus();
  const { isConnected, isConnecting } = useWebSocket();

  const getStatusColor = () => {
    if (isConnecting) return 'text-yellow-500';
    if (isConnected) return 'text-green-500';
    return 'text-red-500';
  };

  const getStatusText = () => {
    if (isConnecting) return 'Connecting...';
    if (isConnected) return 'Connected';
    return 'Disconnected';
  };

  const StatusIcon = isConnecting ? Clock : isConnected ? Wifi : WifiOff;

  return (
    <div className="flex items-center space-x-2 text-sm">
      <StatusIcon className={`h-4 w-4 ${getStatusColor()} ${isConnecting ? 'animate-spin' : ''}`} />
      <span className={getStatusColor()}>{getStatusText()}</span>
      {connectionStatus.reconnectAttempts > 0 && (
        <span className="text-xs text-gray-500">
          (Attempt {connectionStatus.reconnectAttempts})
        </span>
      )}
    </div>
  );
};

export const RealtimeDashboard: React.FC = () => {
  // Filter state
  const [filters, setFilters] = useState<FilterType>({
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Last 30 days
    end_date: new Date().toISOString().split('T')[0], // Today
  });

  // Data fetching with filters
  const { data: dashboard, isLoading: isDashboardLoading, error: dashboardError } = useDashboardAnalytics(filters);
  const { data: spendingTrends } = useSpendingTrends('monthly');
  
  // Real-time data (still useful for live updates)
  const realtimeTransactions = useRealtimeTransactions();
  const notifications = useNotifications();
  const unreadCount = useUnreadNotificationsCount();
  const budgetAlerts = useBudgetAlerts();
  const stats = useRealtimeStats();
  const { refreshDashboard } = useWebSocket();
  
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [updatingStats, setUpdatingStats] = useState<Record<string, boolean>>({});

  // Handle filter changes
  const handleFiltersChange = (newFilters: FilterType) => {
    setFilters(newFilters);
  };

  // WebSocket connection automatically handles message routing

  // Update timestamp when dashboard data changes
  useEffect(() => {
    if (dashboard?.period) {
      setLastUpdate(new Date());
      
      // Show updating animation for stats
      setUpdatingStats({
        balance: true,
        spending: true,
        income: true,
        budget: true
      });
      
      // Clear updating animation after a short delay
      setTimeout(() => {
        setUpdatingStats({});
      }, 1000);
    }
  }, [dashboard]);

  const handleRefresh = () => {
    refreshDashboard();
    setLastUpdate(new Date());
  };

  // Loading state
  if (isDashboardLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (dashboardError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">Failed to load dashboard data</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  // Calculate stats from dashboard data
  const summary = dashboard?.summary;
  const totalIncome = summary?.total_income || 0;
  const totalExpenses = summary?.total_expenses || 0; // Remove Math.abs() - backend already returns positive
  const netAmount = summary?.net_amount || 0;
  const transactionCount = summary?.transaction_count || 0;

  const dashboardStats = [
    {
      id: 'income',
      title: 'Total Income',
      value: formatCurrency(totalIncome),
      change: `${transactionCount} transactions`,
      changeType: 'positive' as const,
      icon: TrendingUp,
    },
    {
      id: 'expenses',
      title: 'Total Expenses',
      value: formatCurrency(totalExpenses),
      change: `Period expenses`,
      changeType: 'negative' as const,
      icon: CreditCard,
    },
    {
      id: 'net',
      title: 'Net Amount',
      value: formatCurrency(netAmount),
      change: netAmount >= 0 ? 'Positive balance' : 'Negative balance',
      changeType: netAmount >= 0 ? ('positive' as const) : ('negative' as const),
      icon: DollarSign,
    },
    {
      id: 'transactions',
      title: 'Transactions',
      value: transactionCount.toString(),
      change: `In selected period`,
      changeType: 'neutral' as const,
      icon: Target,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <div className="flex items-center space-x-4 mt-2">
            <p className="text-gray-600">
              Real-time financial overview
            </p>
            <ConnectionStatus />
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="text-sm text-gray-500">
            Last updated: {formatRelativeTime(lastUpdate.toISOString())}
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
          <StatCard
            key={stat.id}
            {...stat}
            isUpdating={updatingStats[stat.id]}
          />
        ))}
      </div>

      {/* Money Flow Sankey Diagram */}
      <SankeyChart 
        startDate={filters.start_date || ''} 
        endDate={filters.end_date || ''} 
        className="col-span-full"
      />

      {/* Spending Heatmap */}
      <SpendingHeatmap 
        startDate={filters.start_date || ''} 
        endDate={filters.end_date || ''} 
      />

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CategoryPieChart 
          data={dashboard?.category_breakdown || []} 
          title="Spending by Category" 
        />
        <MonthlyComparisonChart 
          data={spendingTrends || []} 
          title="Monthly Trends" 
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
                    {alert.amount && (
                      <div className="font-bold text-yellow-800">
                        {formatCurrency(alert.amount)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Real-time Transaction Feed */}
        <div className="lg:col-span-2">
          <RealtimeTransactionFeed 
            transactions={realtimeTransactions} 
            newCount={stats.newTransactionCount}
          />
        </div>

        {/* Notifications Panel */}
        <div>
          <NotificationPanel 
            notifications={notifications}
            unreadCount={unreadCount}
          />
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">Active Goals</div>
                <div className="text-2xl font-bold">{transactionCount}</div>
              </div>
              <Target className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">Real-time Updates</div>
                <div className="text-2xl font-bold">{stats.transactionCount}</div>
                <div className="text-xs text-gray-500">Transactions tracked</div>
              </div>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
                <span className="text-sm text-green-600">Live</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600">Notifications</div>
                <div className="text-2xl font-bold">{stats.notificationCount}</div>
                {unreadCount > 0 && (
                  <div className="text-xs text-blue-600">{unreadCount} unread</div>
                )}
              </div>
              <div className="relative">
                <AlertCircle className="h-8 w-8 text-gray-400" />
                {unreadCount > 0 && (
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