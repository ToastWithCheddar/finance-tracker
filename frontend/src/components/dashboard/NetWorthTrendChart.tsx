import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui';
import { Alert, AlertDescription } from '../ui/Alert';
import { AlertCircle } from 'lucide-react';
import { useNetWorthTrend } from '../../hooks/useDashboard';
import { formatCurrency } from '../../utils/currency';

interface NetWorthTrendChartProps {
  title?: string;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

const CustomTooltip: React.FC<TooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const value = payload[0].value;
    const formattedDate = new Date(label || '').toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
    
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 dark:text-gray-100 mb-1">{formattedDate}</p>
        <p className="text-sm font-semibold" style={{ color: payload[0].color }}>
          Net Worth: {formatCurrency(value * 100)}
        </p>
      </div>
    );
  }
  return null;
};

const PeriodSelector = ({ 
  selectedPeriod, 
  onPeriodChange 
}: { 
  selectedPeriod: string; 
  onPeriodChange: (period: string) => void;
}) => {
  const periods = [
    { value: '90d', label: '90 Days' },
    { value: '1y', label: '1 Year' },
    { value: 'all', label: 'All Time' }
  ];

  return (
    <div className="flex gap-2">
      {periods.map((period) => (
        <Button
          key={period.value}
          variant={selectedPeriod === period.value ? 'default' : 'outline'}
          size="sm"
          onClick={() => onPeriodChange(period.value)}
          className="text-xs"
        >
          {period.label}
        </Button>
      ))}
    </div>
  );
};

export function NetWorthTrendChart({ title = "Net Worth Trend" }: NetWorthTrendChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState('90d');
  const { data, isLoading, error, isError } = useNetWorthTrend(selectedPeriod);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <PeriodSelector 
              selectedPeriod={selectedPeriod} 
              onPeriodChange={setSelectedPeriod} 
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80">
            <LoadingSpinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <PeriodSelector 
              selectedPeriod={selectedPeriod} 
              onPeriodChange={setSelectedPeriod} 
            />
          </div>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load net worth trend data. {(error as Error)?.message || 'Please try again later.'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <PeriodSelector 
              selectedPeriod={selectedPeriod} 
              onPeriodChange={setSelectedPeriod} 
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80 text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <p>No net worth data available</p>
              <p className="text-sm mt-1">Connect accounts to track your net worth over time</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Determine line color based on trend
  const firstValue = data[0]?.net_worth || 0;
  const lastValue = data[data.length - 1]?.net_worth || 0;
  const isPositiveTrend = lastValue >= firstValue;
  const lineColor = isPositiveTrend ? '#10B981' : '#EF4444';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <PeriodSelector 
            selectedPeriod={selectedPeriod} 
            onPeriodChange={setSelectedPeriod} 
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid 
                strokeDasharray="3 3" 
                className="stroke-gray-200 dark:stroke-gray-600" 
              />
              <XAxis 
                dataKey="date" 
                className="text-gray-600 dark:text-gray-400"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric' 
                  });
                }}
              />
              <YAxis 
                className="text-gray-600 dark:text-gray-400"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => formatCurrency(value * 100)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line 
                type="monotone" 
                dataKey="net_worth" 
                stroke={lineColor}
                strokeWidth={3}
                name="Net Worth"
                dot={{ fill: lineColor, strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {/* Summary Stats */}
        {data.length > 1 && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <p className="text-gray-500 dark:text-gray-400">Start</p>
                <p className="font-semibold">{formatCurrency(firstValue * 100)}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-500 dark:text-gray-400">Current</p>
                <p className="font-semibold">{formatCurrency(lastValue * 100)}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-500 dark:text-gray-400">Change</p>
                <p className={`font-semibold ${isPositiveTrend ? 'text-green-600' : 'text-red-600'}`}>
                  {isPositiveTrend ? '+' : ''}{formatCurrency((lastValue - firstValue) * 100)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}