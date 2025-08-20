import { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui';
import { Alert, AlertDescription } from '../ui/Alert';
import { AlertCircle, Calendar } from 'lucide-react';
import { useCashFlowWaterfall } from '../../hooks/useDashboard';
import { formatCurrency } from '../../utils/currency';

interface CashFlowWaterfallChartProps {
  title?: string;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    payload: WaterfallDataPoint;
  }>;
  label?: string;
}

interface WaterfallDataPoint {
  name: string;
  value: number;
  cumulative: number;
  type: 'start' | 'income' | 'expense' | 'end';
  displayValue: number; // The actual bar height to display
  baseValue: number; // Where the bar should start from
}

const CustomTooltip: React.FC<TooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length && payload[0].payload) {
    const data = payload[0].payload;
    const isNegative = data.type === 'expense';
    
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 dark:text-gray-100 mb-1">{data.name}</p>
        <p className="text-sm font-semibold" style={{ color: payload[0].color }}>
          {isNegative ? 'Expense: ' : ''}{formatCurrency(Math.abs(data.value) * 100)}
        </p>
        {(data.type === 'start' || data.type === 'end') && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Net Worth: {formatCurrency(data.cumulative * 100)}
          </p>
        )}
      </div>
    );
  }
  return null;
};

const DateRangeSelector = ({ 
  startDate, 
  endDate, 
  onDateChange 
}: { 
  startDate: string; 
  endDate: string; 
  onDateChange: (start: string, end: string) => void;
}) => {
  const getDateRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0]
    };
  };

  const presets = [
    { label: '7 Days', days: 7 },
    { label: '30 Days', days: 30 },
    { label: '90 Days', days: 90 }
  ];

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {presets.map((preset) => (
          <Button
            key={preset.days}
            variant="outline"
            size="sm"
            onClick={() => {
              const range = getDateRange(preset.days);
              onDateChange(range.start, range.end);
            }}
            className="text-xs"
          >
            {preset.label}
          </Button>
        ))}
      </div>
      <div className="flex items-center gap-2 ml-2">
        <Calendar className="h-4 w-4 text-gray-500" />
        <input
          type="date"
          value={startDate}
          onChange={(e) => onDateChange(e.target.value, endDate)}
          className="text-xs border rounded px-2 py-1"
        />
        <span className="text-xs text-gray-500">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onDateChange(startDate, e.target.value)}
          className="text-xs border rounded px-2 py-1"
        />
      </div>
    </div>
  );
};

export function CashFlowWaterfallChart({ title = "Cash Flow Waterfall" }: CashFlowWaterfallChartProps) {
  // Default to last 30 days
  const getDefaultDateRange = () => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0]
    };
  };

  const [dateRange, setDateRange] = useState(getDefaultDateRange());
  const { data, isLoading, error, isError } = useCashFlowWaterfall(dateRange.start, dateRange.end);

  const waterfallData = useMemo(() => {
    if (!data) return [];

    let cumulative = data.start_balance;
    const result: WaterfallDataPoint[] = [];

    // Starting balance
    result.push({
      name: 'Starting Balance',
      value: data.start_balance,
      cumulative: cumulative,
      type: 'start',
      displayValue: Math.abs(data.start_balance),
      baseValue: data.start_balance >= 0 ? 0 : data.start_balance
    });

    // Income (positive)
    if (data.total_income > 0) {
      const baseValue = cumulative;
      cumulative += data.total_income;
      result.push({
        name: 'Income',
        value: data.total_income,
        cumulative: cumulative,
        type: 'income',
        displayValue: data.total_income,
        baseValue: baseValue
      });
    }

    // Expenses (negative, but we'll show as positive bars going down from current cumulative)
    if (data.total_expenses > 0) {
      const baseValue = cumulative;
      cumulative -= data.total_expenses;
      result.push({
        name: 'Expenses',
        value: -data.total_expenses, // Negative for display
        cumulative: cumulative,
        type: 'expense',
        displayValue: data.total_expenses,
        baseValue: cumulative // Start from the end position
      });
    }

    // Ending balance
    result.push({
      name: 'Ending Balance',
      value: cumulative,
      cumulative: cumulative,
      type: 'end',
      displayValue: Math.abs(cumulative),
      baseValue: cumulative >= 0 ? 0 : cumulative
    });

    return result;
  }, [data]);

  const handleDateChange = (start: string, end: string) => {
    setDateRange({ start, end });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <DateRangeSelector 
              startDate={dateRange.start}
              endDate={dateRange.end}
              onDateChange={handleDateChange}
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
            <DateRangeSelector 
              startDate={dateRange.start}
              endDate={dateRange.end}
              onDateChange={handleDateChange}
            />
          </div>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load cash flow data. {(error as Error)?.message || 'Please try again later.'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <DateRangeSelector 
              startDate={dateRange.start}
              endDate={dateRange.end}
              onDateChange={handleDateChange}
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80 text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <p>No cash flow data available</p>
              <p className="text-sm mt-1">Connect accounts and add transactions to see cash flow</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getBarColor = (type: string) => {
    switch (type) {
      case 'start':
        return '#6B7280'; // Gray
      case 'income':
        return '#10B981'; // Green
      case 'expense':
        return '#EF4444'; // Red
      case 'end':
        return '#3B82F6'; // Blue
      default:
        return '#6B7280';
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <DateRangeSelector 
            startDate={dateRange.start}
            endDate={dateRange.end}
            onDateChange={handleDateChange}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={waterfallData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-600" />
              <XAxis 
                dataKey="name" 
                className="text-gray-600 dark:text-gray-400"
                tick={{ fontSize: 11 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis 
                className="text-gray-600 dark:text-gray-400"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => formatCurrency(value * 100)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="displayValue" radius={[4, 4, 0, 0]}>
                {waterfallData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.type)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        {/* Summary Stats */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div className="text-center">
              <p className="text-gray-500 dark:text-gray-400">Start</p>
              <p className="font-semibold">{formatCurrency(data.start_balance * 100)}</p>
            </div>
            <div className="text-center">
              <p className="text-green-600">Income</p>
              <p className="font-semibold text-green-600">+{formatCurrency(data.total_income * 100)}</p>
            </div>
            <div className="text-center">
              <p className="text-red-600">Expenses</p>
              <p className="font-semibold text-red-600">-{formatCurrency(data.total_expenses * 100)}</p>
            </div>
            <div className="text-center">
              <p className="text-gray-500 dark:text-gray-400">End</p>
              <p className={`font-semibold ${data.end_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(data.end_balance * 100)}
              </p>
            </div>
          </div>
          <div className="mt-3 text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Net Change: 
              <span className={`ml-1 font-semibold ${(data.end_balance - data.start_balance) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(data.end_balance - data.start_balance) >= 0 ? '+' : ''}
                {formatCurrency((data.end_balance - data.start_balance) * 100)}
              </span>
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}