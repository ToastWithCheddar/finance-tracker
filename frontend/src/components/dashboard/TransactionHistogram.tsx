import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { CHART_COLORS } from '../../utils/chartColors';
import { CurrencyUtils } from '../../utils';
import type { TransactionHistogramData } from '../../services/dashboardService';

interface TransactionHistogramProps {
  data: TransactionHistogramData | null;
  title?: string;
  isLoading?: boolean;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: any;
    value: number;
    dataKey: string;
  }>;
  label?: string;
}

const CustomTooltip: React.FC<ChartTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload;
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 dark:text-gray-100">{data.range_label}</p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Transactions: {data.count}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Total Amount: {CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(data.amount_total)))}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Average: {data.count > 0 ? CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(data.amount_total / data.count))) : '$0.00'}
        </p>
      </div>
    );
  }
  return null;
};

export function TransactionHistogram({ 
  data, 
  title = "Transaction Amount Distribution",
  isLoading = false 
}: TransactionHistogramProps) {
  
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <div className="animate-pulse text-center">
              <p>Loading histogram data...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.bins || data.bins.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <p>No transaction data available</p>
              <p className="text-sm mt-1">No transactions found for the selected period</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Prepare chart data
  const chartData = data.bins.map(bin => ({
    ...bin,
    count: bin.count,
    display_label: bin.range_label.length > 15 
      ? bin.range_label.substring(0, 12) + '...' 
      : bin.range_label
  }));

  const stats = data.statistics;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{title}</span>
          <div className="text-sm font-normal text-gray-500 dark:text-gray-400">
            {stats.total_transactions} transactions
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Key Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Average</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(stats.mean_amount)))}
              </p>
            </div>
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Median</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(stats.median_amount)))}
              </p>
            </div>
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Min</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(stats.min_amount)))}
              </p>
            </div>
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
              <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Max</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(stats.max_amount)))}
              </p>
            </div>
          </div>

          {/* Histogram Chart */}
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 60,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="display_label"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  fontSize={11}
                />
                <YAxis 
                  label={{ value: 'Number of Transactions', angle: -90, position: 'insideLeft' }}
                  fontSize={11}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar 
                  dataKey="count" 
                  fill={CHART_COLORS[0]}
                  name="Transaction Count"
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Additional Info */}
          <div className="text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
            <div className="font-medium text-blue-800 dark:text-blue-200 mb-1">
              📊 Transaction Amount Distribution
            </div>
            <div>
              Showing distribution of {stats.total_transactions} transactions across amount ranges. 
              Total value: {CurrencyUtils.formatCents(CurrencyUtils.dollarsToCents(Math.abs(stats.total_amount)))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}