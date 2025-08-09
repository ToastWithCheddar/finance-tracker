import { useState } from 'react';
import { useAuthUser, useAuthStore } from '../stores/authStore';
import { Button, Card, CardHeader, CardTitle, CardContent, LoadingSpinner } from '../components/ui';
import { LogOut, Plus, TrendingUp, TrendingDown, DollarSign, Target, RefreshCw } from 'lucide-react';
import { useDashboardAnalytics, useSpendingTrends } from '../hooks/useDashboard';
import { CategoryPieChart } from '../components/dashboard/CategoryPieChart';
import { SpendingTrendsChart } from '../components/dashboard/SpendingTrendsChart';
import { MonthlyComparisonChart } from '../components/dashboard/MonthlyComparisonChart';
import { DashboardFilters } from '../components/dashboard/DashboardFilters';
import { AccountsList } from '../components/accounts/AccountsList';
import type { DashboardFilters as FilterType } from '../services/dashboardService';

export function Dashboard() {
  const user = useAuthUser();
  const { logout } = useAuthStore();
  
  // State for filters
  const [filters, setFilters] = useState<FilterType>({
    // Default to current month
    start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
  });

  // Fetch dashboard data
  const { 
    data: dashboardData, 
    isLoading: isDashboardLoading, 
    error: dashboardError,
    refetch: refetchDashboard 
  } = useDashboardAnalytics(filters);
  
  const { 
    data: trendsData, 
    isLoading: isTrendsLoading 
  } = useSpendingTrends('monthly');

  const handleLogout = () => {
    logout();
  };

  const handleRefresh = () => {
    refetchDashboard();
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center mr-3">
                <DollarSign className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Finance Tracker
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Welcome, {user?.displayName ?? user?.email?.split('@')[0]}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={isDashboardLoading}
                className="text-gray-600 hover:text-gray-900"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isDashboardLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-gray-600 hover:text-gray-900"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Message & Filters */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Dashboard
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Here's an overview of your financial activity
              </p>
            </div>
          </div>
          
          {/* Time Period Filters */}
          <DashboardFilters filters={filters} onFiltersChange={setFilters} />
        </div>

        {/* Accounts (includes connect + sync controls) */}
        <div className="mb-8">
          <AccountsList />
        </div>

        {/* Loading State */}
        {isDashboardLoading && (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {/* Error State */}
        {dashboardError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-8">
            <p className="text-red-600 dark:text-red-400">
              Failed to load dashboard data. Please try refreshing the page.
            </p>
          </div>
        )}

        {/* Stats Cards */}
        {dashboardData && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Net Balance</p>
                    <p className={`text-2xl font-bold ${
                      dashboardData.summary.net_amount >= 0 
                        ? 'text-green-600' 
                        : 'text-red-600'
                    }`}>
                      {formatCurrency(dashboardData.summary.net_amount)}
                    </p>
                  </div>
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                    dashboardData.summary.net_amount >= 0 
                      ? 'bg-green-100' 
                      : 'bg-red-100'
                  }`}>
                    <DollarSign className={`h-5 w-5 ${
                      dashboardData.summary.net_amount >= 0 
                        ? 'text-green-600' 
                        : 'text-red-600'
                    }`} />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Income</p>
                    <p className="text-2xl font-bold text-green-600">
                      {formatCurrency(dashboardData.summary.total_income)}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Expenses</p>
                    <p className="text-2xl font-bold text-red-600">
                      {formatCurrency(dashboardData.summary.total_expenses)}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-red-100 rounded-lg flex items-center justify-center">
                    <TrendingDown className="h-5 w-5 text-red-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Transactions</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {dashboardData.summary.transaction_count}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Target className="h-5 w-5 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Charts Section */}
        {dashboardData && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
            {/* Category Pie Chart */}
            <CategoryPieChart 
              data={dashboardData.category_breakdown} 
              title="Spending by Category" 
            />
            
            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Transactions</CardTitle>
              </CardHeader>
              <CardContent>
                {dashboardData.recent_transactions.length > 0 ? (
                  <div className="space-y-3">
                    {dashboardData.recent_transactions.slice(0, 8).map((transaction) => (
                      <div key={transaction.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="flex-1">
                          <p className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                            {transaction.description || 'No description'}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {transaction.category || 'Uncategorized'} • {new Date(transaction.transaction_date).toLocaleDateString()}
                          </p>
                        </div>
                        <div className={`text-right ${
                          transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          <p className="font-medium text-sm">
                            {transaction.amount >= 0 ? '+' : ''}{formatCurrency(transaction.amount)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <p>No transactions yet</p>
                    <p className="text-sm mt-1">Add your first transaction to get started</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Trends Charts */}
        {(dashboardData || trendsData) && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
            {/* Spending Trends Line Chart */}
            {trendsData && !isTrendsLoading && (
              <SpendingTrendsChart 
                data={trendsData} 
                title="Monthly Spending Trends" 
              />
            )}
            
            {/* Monthly Comparison Bar Chart */}
            {trendsData && !isTrendsLoading && (
              <MonthlyComparisonChart 
                data={trendsData} 
                title="Income vs Expenses" 
              />
            )}
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <Button className="h-20 flex-col">
                  <Plus className="h-6 w-6 mb-2" />
                  Add Transaction
                </Button>
                <Button variant="secondary" className="h-20 flex-col">
                  <Target className="h-6 w-6 mb-2" />
                  Set Budget
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Period Summary */}
          {dashboardData && (
            <Card>
              <CardHeader>
                <CardTitle>Period Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Period:</span>
                    <span className="text-sm font-medium">
                      {new Date(dashboardData.period.start_date).toLocaleDateString()} - {new Date(dashboardData.period.end_date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="h-px bg-gray-200 dark:bg-gray-600"></div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Total Transactions:</span>
                    <span className="text-sm font-medium">{dashboardData.summary.transaction_count}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Categories Used:</span>
                    <span className="text-sm font-medium">{dashboardData.category_breakdown.length}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Net Change:</span>
                    <span className={`text-sm font-medium ${
                      dashboardData.summary.net_amount >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(dashboardData.summary.net_amount)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Getting Started - Only show if no data */}
        {(!dashboardData || dashboardData.summary.transaction_count === 0) && (
          <Card>
            <CardHeader>
              <CardTitle>Getting Started</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold text-sm mr-4">
                    1
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-gray-100">Add your first transaction</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Track your income and expenses</p>
                  </div>
                </div>
                
                <div className="flex items-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="h-8 w-8 bg-gray-400 rounded-full flex items-center justify-center text-white font-bold text-sm mr-4">
                    2
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-gray-100">Set up categories</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Organize your spending</p>
                  </div>
                </div>
                
                <div className="flex items-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="h-8 w-8 bg-gray-400 rounded-full flex items-center justify-center text-white font-bold text-sm mr-4">
                    3
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-gray-100">Create budgets</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Set spending limits and goals</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}