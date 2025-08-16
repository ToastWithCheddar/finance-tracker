import { useDashboardAnalytics, useSpendingTrends } from '../hooks/useDashboard';
import { useWebSocket } from '../hooks/useWebSocket';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/Alert';
import { formatCurrency } from '../utils/currency';
import { TrendingUp, ArrowRightLeft, BarChart, AlertCircle } from 'lucide-react';
import { AccountsList } from '../components/accounts/AccountsList';
import { SpendingTrendsChart } from '../components/dashboard/SpendingTrendsChart';
import MonthlyComparisonChart from '../components/dashboard/MonthlyComparisonChart';
import { RealtimeTransactionFeed } from '../components/dashboard/RealtimeTransactionFeed';
import { NotificationPanel } from '../components/dashboard/NotificationPanel';
import { useNotifications, useRealtimeTransactions } from '../stores/realtimeStore';

const MetricCard = ({ title, value, icon: Icon }: { title: string; value: string; icon: React.ElementType }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-[hsl(var(--text))/0.6]" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
    </CardContent>
  </Card>
);

const RecentTransactionItem = ({ description, amountCents, date }: { description: string; amountCents: number; date: string }) => (
  <div className="flex items-center justify-between">
    <div>
      <p className="text-sm font-medium">{description}</p>
      <p className="text-xs text-muted-foreground">{new Date(date).toLocaleDateString()}</p>
    </div>
    <div className={`text-sm font-semibold ${amountCents < 0 ? 'text-red-500' : 'text-green-500'}`}>
      {formatCurrency(amountCents)}
    </div>
  </div>
);

const SpendingByCategoryItem = ({ category, amountCents }: { category: string; amountCents: number }) => (
  <div className="flex items-center justify-between py-2">
    <p className="text-sm">{category}</p>
    <p className="text-sm font-semibold">{formatCurrency(amountCents)}</p>
  </div>
);

const QuickFilterButtons = () => {
  const navigate = useNavigate();

  const getDateString = (daysAgo: number): string => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    return date.toISOString().split('T')[0];
  };

  const getCurrentDateString = (): string => {
    return new Date().toISOString().split('T')[0];
  };

  const handleQuickFilter = (days: number, label: string) => {
    const dateTo = getCurrentDateString();
    const dateFrom = getDateString(days);
    navigate(`/transactions?dateFrom=${dateFrom}&dateTo=${dateTo}`);
  };

  return (
    <div className="flex gap-2">
      <Button 
        variant="outline" 
        size="sm"
        onClick={() => handleQuickFilter(1, '1 Day')}
        className="text-xs"
      >
        1 Day
      </Button>
      <Button 
        variant="outline" 
        size="sm"
        onClick={() => handleQuickFilter(7, '1 Week')}
        className="text-xs"
      >
        1 Week
      </Button>
      <Button 
        variant="outline" 
        size="sm"
        onClick={() => handleQuickFilter(30, '1 Month')}
        className="text-xs"
      >
        1 Month
      </Button>
    </div>
  );
};

export function Dashboard() {
  // Initialize WebSocket connection for real-time updates
  useWebSocket();

  const { data, isLoading, error, isError } = useDashboardAnalytics();
  const { data: trends = [] } = useSpendingTrends('monthly');
  const notifications = useNotifications();
  const realtimeTransactions = useRealtimeTransactions();

  if (isLoading) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Skeleton loaders */}
          <Card className="h-28 animate-pulse bg-[hsl(var(--border)/0.35)]" />
          <Card className="h-28 animate-pulse bg-[hsl(var(--border)/0.35)]" />
        </div>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <Card className="h-64 animate-pulse bg-[hsl(var(--border)/0.35)]" />
          <Card className="h-64 animate-pulse bg-[hsl(var(--border)/0.35)]" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load dashboard data. {(error as Error)?.message || 'Please try again later.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>

      {/* Bank Connections - First Priority */}
      <AccountsList />

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Balance"
          value={formatCurrency((data?.totalBalance ?? 0) * 100)}
          icon={TrendingUp}
        />
        <MetricCard
          title="Total Transactions"
          value={data?.totalTransactions.toLocaleString() ?? '0'}
          icon={ArrowRightLeft}
        />
      </div>

      {/* Trends and Money Flow */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SpendingTrendsChart data={trends} />
        <MonthlyComparisonChart data={trends} />
      </div>

      {/* Live Feed and Notifications */}
      <div className="grid gap-6 lg:grid-cols-2">
        <RealtimeTransactionFeed transactions={realtimeTransactions} newCount={realtimeTransactions.filter(t => t.isNew).length} />
        <NotificationPanel notifications={notifications} unreadCount={notifications.filter(n => !n.read).length} />
      </div>

      {/* Recent Transactions & Spending by Category */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Transactions</CardTitle>
              <QuickFilterButtons />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {data?.recentTransactions.length ? (
              <div className="max-h-80 overflow-y-auto divide-y divide-[hsl(var(--border))]">
                {data.recentTransactions.map(tx => (
                  <div key={tx.id} className="px-6 py-3">
                    <RecentTransactionItem {...tx} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6">
                <p className="text-sm text-[hsl(var(--text))/0.7]">No recent transactions.</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Spending by Category</CardTitle>
          </CardHeader>
          <CardContent>
            {data?.spendingByCategory && Object.keys(data.spendingByCategory).length > 0 ? (
              Object.entries(data.spendingByCategory).map(([category, amountCents]) => (
                <SpendingByCategoryItem key={category} category={category} amountCents={amountCents} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No spending data available.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}