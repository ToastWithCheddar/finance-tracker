import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { CHART_COLORS } from '../../utils/chartColors';
import type { CategoryBreakdown } from '../../services/dashboardService';

interface CategoryPieChartProps {
  data: CategoryBreakdown[];
  title?: string;
}


interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: CategoryBreakdown;
    value: number;
  }>;
}

const CustomTooltip: React.FC<TooltipProps> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 dark:text-gray-100">{data.category_name}</p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Amount: ${Math.abs(data.total_amount).toFixed(2)}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Transactions: {data.transaction_count}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Percentage: {(Number((data as any).percentage_expense ?? data.percentage) as number).toFixed(1)}%
        </p>
      </div>
    );
  }
  return null;
};

export function CategoryPieChart({ data, title = "Spending by Category" }: CategoryPieChartProps) {
  // Prepare expense-only data and recompute percentages relative to total expenses
  const expensesOnly = data.filter(item => item.total_amount < 0);
  const totalExpenseAbs = expensesOnly.reduce((sum, it) => sum + Math.abs(it.total_amount), 0) || 0;
  const chartData = expensesOnly
    .slice(0, 10)
    .map(item => {
      const value = Math.abs(item.total_amount);
      const pct = totalExpenseAbs > 0 ? (value / totalExpenseAbs) * 100 : 0;
      return {
        ...item,
        value,
        percentage_expense: pct,
      } as any;
    });

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <p>No spending data available</p>
              <p className="text-sm mt-1">Add some expenses to see the breakdown</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
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
                // Use recomputed expense-only percentage for labels
                label={({ category_name, percentage_expense }: any) => `${category_name} ${Number(percentage_expense).toFixed(1)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
