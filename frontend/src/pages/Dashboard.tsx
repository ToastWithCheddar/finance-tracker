import { useDashboardAnalytics } from '../hooks/useDashboardAnalytics';
import { useWebSocket } from '../hooks/useWebSocket';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/Alert';
import { formatCurrency } from '../utils/currency';
import { TrendingUp, ArrowRightLeft, BarChart, AlertCircle } from 'lucide-react';

const MetricCard = ({ title, value, icon: Icon }: { title: string; value: string; icon: React.ElementType }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
    </CardContent>
  </Card>
);

const RecentTransactionItem = ({ description, amountCents, date }: { description: string; amountCents: number; date: string }) => (
  <div className="flex items-center justify-between py-2">
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

export function Dashboard() {
  // Initialize WebSocket connection for real-time updates
  useWebSocket();

  const { data, isLoading, error, isError } = useDashboardAnalytics();

  if (isLoading) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Skeleton loaders */}
          <Card className="h-28 animate-pulse bg-gray-200 dark:bg-gray-800" />
          <Card className="h-28 animate-pulse bg-gray-200 dark:bg-gray-800" />
        </div>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <Card className="h-64 animate-pulse bg-gray-200 dark:bg-gray-800" />
          <Card className="h-64 animate-pulse bg-gray-200 dark:bg-gray-800" />
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

      {/* Recent Transactions & Spending by Category */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Transactions</CardTitle>
          </CardHeader>
          <CardContent>
            {data?.recentTransactions.length ? (
              data.recentTransactions.map(tx => <RecentTransactionItem key={tx.id} {...tx} />)
            ) : (
              <p className="text-sm text-muted-foreground">No recent transactions.</p>
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