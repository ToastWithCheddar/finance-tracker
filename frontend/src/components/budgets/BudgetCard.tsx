import { useState } from 'react';
import { PencilIcon, TrashIcon, AlertTriangleIcon, TrendingUpIcon, TrendingDownIcon, Bell, Settings, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { budgetService } from '../../services/budgetService';
import type { Budget } from '../../types/budgets';

interface BudgetCardProps {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  onDelete: (budgetId: string) => void;
  onOpenAlertSettings: () => void;
  onOpenCalendar: () => void;
  isLoading?: boolean;
}

export function BudgetCard({ 
  budget, 
  onEdit, 
  onDelete, 
  onOpenAlertSettings, 
  onOpenCalendar, 
  isLoading = false 
}: BudgetCardProps) {
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const handleDelete = () => {
    setShowConfirmDelete(true);
  };

  const handleConfirmDelete = () => {
    onDelete(budget.id);
    setShowConfirmDelete(false);
  };

  const handleCancelDelete = () => {
    setShowConfirmDelete(false);
  };

  const status = budgetService.getBudgetStatus(budget.usage);
  const statusColor = budgetService.getBudgetStatusColor(status);
  const statusBgColor = budgetService.getBudgetStatusBgColor(status);

  const percentageUsed = budget.usage?.percentage_used || 0;
  const progressWidth = Math.min(percentageUsed, 100);

  const getBudgetTheme = () => {
    const percentageUsed = budget.usage?.percentage_used || 0;
    if (budget.usage?.is_over_budget) {
      return {
        cardClass: 'bg-expense-gradient border-expense-300 dark:border-expense-600 shadow-lg shadow-expense-100/50 dark:shadow-expense-800/50 ring-1 ring-expense-200 dark:ring-expense-700',
        headerColor: 'text-expense-900 dark:text-expense-100',
        progressClass: 'progress-bar-danger'
      };
    } else if (percentageUsed >= 80) {
      return {
        cardClass: 'bg-warning-gradient border-yellow-300 dark:border-yellow-600 shadow-lg shadow-yellow-100/50 dark:shadow-yellow-800/50 ring-1 ring-yellow-200 dark:ring-yellow-700',
        headerColor: 'text-yellow-900 dark:text-yellow-100',
        progressClass: 'progress-bar-warning'
      };
    } else {
      return {
        cardClass: 'bg-budget-gradient border-budget-300 dark:border-budget-600 shadow-lg shadow-budget-100/50 dark:shadow-budget-800/50 ring-1 ring-budget-200 dark:ring-budget-700',
        headerColor: 'text-budget-900 dark:text-budget-100',
        progressClass: 'progress-bar-success'
      };
    }
  };

  const theme = getBudgetTheme();

  return (
    <Card className={`
      ${theme.cardClass}
      card-hover
      backdrop-blur-sm
      ${isLoading ? 'opacity-50 shimmer' : ''} 
      transition-all duration-300
      ${budget.usage?.is_over_budget ? 'animate-bounce-gentle' : ''}
    `}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className={`text-lg font-bold ${theme.headerColor}`}>
                {budget.name}
              </h3>
              {budget.usage?.is_over_budget && (
                <div className="relative">
                  <AlertTriangleIcon className="h-5 w-5 text-expense-600 animate-pulse" />
                  <div className="absolute inset-0 animate-ping">
                    <AlertTriangleIcon className="h-5 w-5 text-expense-600 opacity-75" />
                  </div>
                </div>
              )}
            </div>
            
            {budget.category_name && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Category: {budget.category_name}
              </p>
            )}
            
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-600 dark:text-gray-400">
                {budgetService.getPeriodDisplayName(budget.period)}
              </span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusBgColor} ${statusColor}`}>
                {status.replace('-', ' ')}
              </span>
              {budget.has_custom_alerts && (
                <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 rounded-full text-xs font-medium">
                  <Bell className="h-3 w-3" />
                  Custom
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onOpenCalendar}
              disabled={isLoading}
              className="h-8 w-8 p-0"
              title="Calendar View"
            >
              <Calendar className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onOpenAlertSettings}
              disabled={isLoading}
              className="h-8 w-8 p-0"
              title="Alert Settings"
            >
              <Bell className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(budget)}
              disabled={isLoading}
              className="h-8 w-8 p-0"
              title="Edit Budget"
            >
              <PencilIcon className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              disabled={isLoading}
              className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
              title="Delete Budget"
            >
              <TrashIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Budget Amount */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {budgetService.formatCurrency(budget.amount_cents)}
            </span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {budgetService.calculateDaysRemaining(budget.usage)}
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        {budget.usage && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-semibold ${theme.headerColor}`}>
                Progress
              </span>
              <span className={`text-sm font-bold px-2 py-1 rounded-full bg-white/20 backdrop-blur-sm ${theme.headerColor}`}>
                {budgetService.formatPercentage(percentageUsed)}
              </span>
            </div>
            
            <div className="relative">
              <div className="w-full bg-white/30 dark:bg-gray-800/50 rounded-full h-3 shadow-inner backdrop-blur-sm">
                <div
                  className={`h-3 rounded-full transition-all duration-700 ease-out shadow-lg ${theme.progressClass} relative overflow-hidden`}
                  style={{ width: `${progressWidth}%` }}
                >
                  {/* Shimmer effect for active progress */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                </div>
              </div>
              {/* Glow effect for over-budget */}
              {budget.usage.is_over_budget && (
                <div className="absolute inset-0 rounded-full bg-expense-400/20 animate-pulse"></div>
              )}
            </div>
          </div>
        )}

        {/* Spending Details */}
        {budget.usage && (
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center bg-white/20 dark:bg-gray-800/30 rounded-xl p-3 backdrop-blur-sm border border-white/30 dark:border-gray-700/50">
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className="p-1 rounded-full bg-expense-100 dark:bg-expense-800">
                  <TrendingDownIcon className="h-4 w-4 text-expense-600 dark:text-expense-400" />
                </div>
                <span className={`text-xs font-semibold ${theme.headerColor}`}>
                  Spent
                </span>
              </div>
              <p className="text-lg font-bold text-expense-700 dark:text-expense-300">
                {budgetService.formatCurrency(budget.usage.spent_cents)}
              </p>
            </div>
            
            <div className="text-center bg-white/20 dark:bg-gray-800/30 rounded-xl p-3 backdrop-blur-sm border border-white/30 dark:border-gray-700/50">
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className={`p-1 rounded-full ${
                  budget.usage.remaining_cents >= 0 
                    ? 'bg-success-100 dark:bg-success-800' 
                    : 'bg-expense-100 dark:bg-expense-800'
                }`}>
                  <TrendingUpIcon className={`h-4 w-4 ${
                    budget.usage.remaining_cents >= 0 
                      ? 'text-success-600 dark:text-success-400' 
                      : 'text-expense-600 dark:text-expense-400'
                  }`} />
                </div>
                <span className={`text-xs font-semibold ${theme.headerColor}`}>
                  Remaining
                </span>
              </div>
              <p className={`text-lg font-bold ${
                budget.usage.remaining_cents >= 0 
                  ? 'text-success-700 dark:text-success-300' 
                  : 'text-expense-700 dark:text-expense-300'
              }`}>
                {budgetService.formatCurrency(budget.usage.remaining_cents)}
              </p>
            </div>
          </div>
        )}

        {/* Over Budget Warning */}
        {budget.usage?.is_over_budget && (
          <div className="mt-4 p-4 bg-gradient-to-r from-expense-100 via-expense-50 to-expense-100 dark:from-expense-900/40 dark:via-expense-800/30 dark:to-expense-900/40 border-2 border-expense-300 dark:border-expense-600 rounded-xl shadow-lg shadow-expense-200/50 dark:shadow-expense-800/50 animate-bounce-gentle">
            <div className="flex items-center justify-between">
              <div className="flex items-center text-expense-800 dark:text-expense-200">
                <div className="relative mr-3">
                  <AlertTriangleIcon className="h-6 w-6 animate-pulse" />
                  <div className="absolute inset-0 animate-ping">
                    <AlertTriangleIcon className="h-6 w-6 opacity-75" />
                  </div>
                </div>
                <div>
                  <div className="font-bold text-sm">OVER BUDGET</div>
                  <div className="text-xs opacity-80">
                    Exceeded by {budgetService.formatCurrency(budget.usage.spent_cents - budget.amount_cents)}
                  </div>
                </div>
              </div>
              <div className="text-2xl">🚨</div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        <Modal 
          isOpen={showConfirmDelete} 
          onClose={handleCancelDelete} 
          size="sm"
        >
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-800 rounded-lg">
                  <AlertTriangleIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <CardTitle>Delete Budget</CardTitle>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    This action cannot be undone
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-700 dark:text-gray-300">
                Are you sure you want to delete the budget "{budget.name}"? This will permanently remove all budget data and settings.
              </p>
              <div className="flex items-center justify-end gap-3 pt-4">
                <Button
                  variant="ghost"
                  onClick={handleCancelDelete}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleConfirmDelete}
                  disabled={isLoading}
                >
                  {isLoading ? 'Deleting...' : 'Delete Budget'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </Modal>
      </CardContent>
    </Card>
  );
}