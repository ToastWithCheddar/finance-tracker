import { useState, useMemo } from 'react';
import { ResponsiveCalendar } from '@nivo/calendar';
import { 
  Calendar,
  ChevronLeft,
  ChevronRight,
  X,
  TrendingUp,
  DollarSign,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { useBudgetCalendar } from '../../hooks/useBudgets';
import { useChartTheme } from '../../hooks/useChartTheme';
import { budgetService } from '../../services/budgetService';
import type { Budget, BudgetCalendarDay } from '../../types/budgets';

interface BudgetCalendarProps {
  budget: Budget;
  isOpen: boolean;
  onClose: () => void;
}

// Custom tooltip component moved outside render function for better performance
const CustomTooltip = ({ day, value, data }: any) => {
  const dayData = data;
  if (!dayData) return null;

  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 min-w-48">
      <div className="font-medium text-gray-900 dark:text-gray-100 mb-2">
        {new Date(day).toLocaleDateString('en-US', {
          weekday: 'long',
          month: 'short',
          day: 'numeric'
        })}
      </div>
      
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Spent:</span>
          <span className="font-medium text-red-600 dark:text-red-400">
            ${value?.toFixed(2) || '0.00'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Daily Limit:</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            ${dayData.dailyLimit?.toFixed(2) || '0.00'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Usage:</span>
          <span className={`font-medium ${
            dayData.isOverLimit 
              ? 'text-red-600 dark:text-red-400' 
              : dayData.percentage > 80 
                ? 'text-yellow-600 dark:text-yellow-400'
                : 'text-green-600 dark:text-green-400'
          }`}>
            {dayData.percentage?.toFixed(1) || 0}%
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Transactions:</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {dayData.transactionCount || 0}
          </span>
        </div>
        
        {dayData.isOverLimit && (
          <div className="mt-2 flex items-center gap-1 text-red-600 dark:text-red-400">
            <AlertTriangle className="h-3 w-3" />
            <span className="text-xs font-medium">Over daily limit</span>
          </div>
        )}
      </div>
    </div>
  );
};

export function BudgetCalendar({ budget, isOpen, onClose }: BudgetCalendarProps) {
  const currentDate = new Date();
  const [selectedMonth, setSelectedMonth] = useState(
    `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}`
  );

  const { data: calendarData, isLoading, error } = useBudgetCalendar(budget.id, selectedMonth);
  const { theme } = useChartTheme();

  // Transform data for Nivo Calendar
  const nivoData = useMemo(() => {
    if (!calendarData) return [];

    return calendarData.daily_data.map((day: BudgetCalendarDay) => ({
      day: day.date,
      value: day.actual_spending_cents / 100, // Convert to dollars for display
      percentage: day.percentage_used,
      isOverLimit: day.is_over_limit,
      dailyLimit: day.daily_spending_limit_cents / 100,
      transactionCount: day.transactions_count
    }));
  }, [calendarData]);

  // Calendar navigation
  const handlePreviousMonth = () => {
    const [year, month] = selectedMonth.split('-').map(Number);
    const prevMonth = month === 1 ? 12 : month - 1;
    const prevYear = month === 1 ? year - 1 : year;
    setSelectedMonth(`${prevYear}-${String(prevMonth).padStart(2, '0')}`);
  };

  const handleNextMonth = () => {
    const [year, month] = selectedMonth.split('-').map(Number);
    const nextMonth = month === 12 ? 1 : month + 1;
    const nextYear = month === 12 ? year + 1 : year;
    setSelectedMonth(`${nextYear}-${String(nextMonth).padStart(2, '0')}`);
  };

  const formatMonthYear = (monthStr: string) => {
    const [year, month] = monthStr.split('-').map(Number);
    return new Date(year, month - 1).toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric'
    });
  };


  if (isLoading) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          </CardContent>
        </Card>
      </Modal>
    );
  }

  if (error) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                <p className="text-red-600 dark:text-red-400">Failed to load calendar data</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </Modal>
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-800 rounded-lg">
                <Calendar className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <CardTitle>Budget Calendar</CardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Daily spending view for "{budget.name}"
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Month Navigation */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviousMonth}
              className="flex items-center gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {formatMonthYear(selectedMonth)}
            </h3>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextMonth}
              className="flex items-center gap-2"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Summary Stats */}
          {calendarData && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                    Total Spent
                  </span>
                </div>
                <p className="text-lg font-bold text-blue-900 dark:text-blue-100">
                  {budgetService.formatCurrency(calendarData.summary.total_spending_cents)}
                </p>
              </div>

              <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium text-green-900 dark:text-green-100">
                    Budget Progress
                  </span>
                </div>
                <p className="text-lg font-bold text-green-900 dark:text-green-100">
                  {calendarData.summary.month_progress_percentage.toFixed(1)}%
                </p>
              </div>

              <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                    Days Active
                  </span>
                </div>
                <p className="text-lg font-bold text-yellow-900 dark:text-yellow-100">
                  {calendarData.summary.days_with_budget} / {calendarData.summary.days_in_month}
                </p>
              </div>

              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <span className="text-sm font-medium text-red-900 dark:text-red-100">
                    Over Limit
                  </span>
                </div>
                <p className="text-lg font-bold text-red-900 dark:text-red-100">
                  {calendarData.summary.days_over_limit} days
                </p>
              </div>
            </div>
          )}

          {/* Calendar */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div style={{ height: '400px' }}>
              <ResponsiveCalendar
                data={nivoData}
                from={`${selectedMonth}-01`}
                to={`${selectedMonth}-31`}
                emptyColor="#f3f4f6"
                colors={[
                  '#22c55e', // Green - under budget
                  '#eab308', // Yellow - getting close
                  '#f59e0b', // Orange - close to limit
                  '#ef4444', // Red - over budget
                ]}
                margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                yearSpacing={40}
                monthBorderColor="#e5e7eb"
                dayBorderWidth={1}
                dayBorderColor="#e5e7eb"
                tooltip={CustomTooltip}
                theme={theme}
                minValue={0}
                maxValue="auto"
                daySpacing={2}
                monthSpacing={10}
              />
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span className="text-gray-600 dark:text-gray-400">Under Budget</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span className="text-gray-600 dark:text-gray-400">Close to Limit</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-500 rounded"></div>
              <span className="text-gray-600 dark:text-gray-400">Near Limit</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span className="text-gray-600 dark:text-gray-400">Over Limit</span>
            </div>
          </div>

          {/* Average Daily Spending */}
          {calendarData && (
            <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">
                    Average Daily Spending
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Based on active budget days
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {budgetService.formatCurrency(calendarData.summary.average_daily_spending_cents)}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    per day
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </Modal>
  );
}