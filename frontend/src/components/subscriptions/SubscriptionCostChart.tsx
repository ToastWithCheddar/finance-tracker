import React, { useMemo } from 'react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { formatCurrency } from '../../utils/currency';
import { CHART_COLORS, FREQUENCY_COLORS } from '../../utils/categoryColors';
import type { UnifiedSubscription, SubscriptionAnalytics } from '../../types/subscription';

interface SubscriptionCostChartProps {
  subscriptions: UnifiedSubscription[];
  analytics: SubscriptionAnalytics;
}

interface ChartDataPoint {
  name: string;
  value: number;
  count: number;
  color: string;
}



const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 dark:text-gray-100">{label || data.name}</p>
        <p className="text-blue-600 dark:text-blue-400">
          Amount: {formatCurrency(data.value / 100)}
        </p>
        {data.count && (
          <p className="text-gray-600 dark:text-gray-400">
            Subscriptions: {data.count}
          </p>
        )}
      </div>
    );
  }
  return null;
};

const CategoryPieChart: React.FC<{ analytics: SubscriptionAnalytics }> = ({ analytics }) => {
  const chartData = useMemo(() => {
    return analytics.categoryBreakdown.slice(0, 8).map((category, index) => ({
      name: category.categoryName,
      value: category.amountCents,
      count: category.count,
      color: CHART_COLORS[index % CHART_COLORS.length]
    }));
  }, [analytics.categoryBreakdown]);

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null; // Don't show labels for slices < 5%
    
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Spending Distribution by Category</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderCustomLabel}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        {/* Legend */}
        <div className="grid grid-cols-2 gap-2 mt-4">
          {chartData.map((entry, index) => (
            <div key={entry.name} className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-sm text-[hsl(var(--text))] truncate">
                {entry.name}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

const FrequencyBarChart: React.FC<{ analytics: SubscriptionAnalytics }> = ({ analytics }) => {
  const chartData = useMemo(() => {
    return Object.entries(analytics.frequencyBreakdown).map(([frequency, data]) => ({
      name: frequency.charAt(0).toUpperCase() + frequency.slice(1).toLowerCase(),
      amount: data.totalCents,
      count: data.count,
      color: FREQUENCY_COLORS[frequency as keyof typeof FREQUENCY_COLORS] || '#6b7280'
    }));
  }, [analytics.frequencyBreakdown]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Monthly Cost by Payment Frequency</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
              <XAxis 
                dataKey="name" 
                className="text-gray-600 dark:text-gray-400"
                fontSize={12}
              />
              <YAxis 
                className="text-gray-600 dark:text-gray-400"
                fontSize={12}
                tickFormatter={(value) => `$${(value / 100).toFixed(0)}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar 
                dataKey="amount" 
                radius={[4, 4, 0, 0]}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

const TopSubscriptionsChart: React.FC<{ subscriptions: UnifiedSubscription[] }> = ({ subscriptions }) => {
  const chartData = useMemo(() => {
    return subscriptions
      .filter(s => s.isActive && !s.isMuted)
      .sort((a, b) => b.monthlyEstimatedCents - a.monthlyEstimatedCents)
      .slice(0, 10)
      .map((subscription, index) => ({
        name: subscription.name.length > 20 
          ? subscription.name.substring(0, 20) + '...' 
          : subscription.name,
        amount: subscription.monthlyEstimatedCents,
        frequency: subscription.frequency,
        color: CHART_COLORS[index % CHART_COLORS.length]
      }));
  }, [subscriptions]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top 10 Subscriptions by Cost</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart 
              data={chartData} 
              layout="horizontal"
              margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
              <XAxis 
                type="number" 
                className="text-gray-600 dark:text-gray-400"
                fontSize={12}
                tickFormatter={(value) => `$${(value / 100).toFixed(0)}`}
              />
              <YAxis 
                type="category" 
                dataKey="name" 
                className="text-gray-600 dark:text-gray-400"
                fontSize={11}
                width={100}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar 
                dataKey="amount" 
                radius={[0, 4, 4, 0]}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

const SourceComparisonChart: React.FC<{ analytics: SubscriptionAnalytics }> = ({ analytics }) => {
  const chartData = [
    {
      name: 'Plaid Detected',
      amount: analytics.sourceBreakdown.plaid.totalCents,
      count: analytics.sourceBreakdown.plaid.count,
      color: '#3b82f6'
    },
    {
      name: 'Manual Rules',
      amount: analytics.sourceBreakdown.manual.totalCents,
      count: analytics.sourceBreakdown.manual.count,
      color: '#10b981'
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost by Data Source</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
              <XAxis 
                dataKey="name" 
                className="text-gray-600 dark:text-gray-400"
                fontSize={12}
              />
              <YAxis 
                className="text-gray-600 dark:text-gray-400"
                fontSize={12}
                tickFormatter={(value) => `$${(value / 100).toFixed(0)}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar 
                dataKey="amount" 
                radius={[4, 4, 0, 0]}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * Chart collection component that provides various visualizations of subscription
 * cost data including category breakdown, frequency analysis, top subscriptions,
 * and data source comparison using recharts.
 */
export const SubscriptionCostChart: React.FC<SubscriptionCostChartProps> = ({ 
  subscriptions, 
  analytics 
}) => {
  // Don't render charts if there's no data
  if (subscriptions.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <p className="text-[hsl(var(--text))] opacity-70">
            No subscription data available for visualization
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Primary Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CategoryPieChart analytics={analytics} />
        <FrequencyBarChart analytics={analytics} />
      </div>
      
      {/* Secondary Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TopSubscriptionsChart subscriptions={subscriptions} />
        <SourceComparisonChart analytics={analytics} />
      </div>
    </div>
  );
};