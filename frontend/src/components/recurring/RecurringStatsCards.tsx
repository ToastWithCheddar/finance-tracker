import React from 'react';
import { 
  Activity, 
  Clock, 
  DollarSign, 
  AlertTriangle,
  Calendar,
  TrendingUp
} from 'lucide-react';
import type { RecurringRuleStats } from '../../types/recurring';
import { Card } from '../ui/Card';
import { formatCurrency } from '../../utils/currency';

interface RecurringStatsCardsProps {
  stats: RecurringRuleStats;
}

export const RecurringStatsCards: React.FC<RecurringStatsCardsProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Monthly Amount */}
      <Card>
        <div className="p-4">
          <div className="flex items-center">
            <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900">
              <DollarSign className="h-6 w-6 text-blue-600 dark:text-blue-200" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">
                {formatCurrency(stats.total_monthly_amount_cents / 100)}
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Monthly Total</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Active Rules */}
      <Card>
        <div className="p-4">
          <div className="flex items-center">
            <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-green-100 dark:bg-green-900">
              <Activity className="h-6 w-6 text-green-600 dark:text-green-200" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">
                {stats.active_rules}
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">
                Active Rules ({stats.total_rules} total)
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Due This Week */}
      <Card>
        <div className="p-4">
          <div className="flex items-center">
            <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-orange-100 dark:bg-orange-900">
              <Clock className="h-6 w-6 text-orange-600 dark:text-orange-200" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-[hsl(var(--text))]">
                {stats.due_this_week}
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Due This Week</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Overdue */}
      <Card>
        <div className="p-4">
          <div className="flex items-center">
            <div className={`flex items-center justify-center h-12 w-12 rounded-lg ${
              stats.overdue > 0 ? 'bg-red-100 dark:bg-red-900' : 'bg-gray-100 dark:bg-gray-800'
            }`}>
              <AlertTriangle className={`h-6 w-6 ${
                stats.overdue > 0 ? 'text-red-600 dark:text-red-200' : 'text-gray-400 dark:text-gray-500'
              }`} />
            </div>
            <div className="ml-4">
              <p className={`text-2xl font-bold text-[hsl(var(--text))]`}>
                {stats.overdue}
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">Overdue</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Frequency Breakdown */}
      <Card className="md:col-span-2">
        <div className="p-4">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-3 flex items-center">
            <Calendar className="h-5 w-5 mr-2 text-blue-600 dark:text-blue-300" />
            Frequency Breakdown
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Weekly:</span>
              <span className="font-medium">{stats.weekly_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Monthly:</span>
              <span className="font-medium">{stats.monthly_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Quarterly:</span>
              <span className="font-medium">{stats.quarterly_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Annual:</span>
              <span className="font-medium">{stats.annual_count}</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Additional Stats */}
      <Card className="md:col-span-2">
        <div className="p-4">
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-3 flex items-center">
            <TrendingUp className="h-5 w-5 mr-2 text-green-600 dark:text-green-300" />
            Additional Statistics
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Average amount:</span>
              <span className="font-medium">
                {formatCurrency(stats.average_amount_cents / 100)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Confirmed rules:</span>
              <span className="font-medium">{stats.confirmed_rules}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Suggested rules:</span>
              <span className="font-medium">{stats.suggested_rules}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">Due next week:</span>
              <span className="font-medium">{stats.due_next_week}</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};