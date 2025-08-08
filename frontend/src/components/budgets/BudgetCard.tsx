import { useState } from 'react';
import { PencilIcon, TrashIcon, AlertTriangleIcon, TrendingUpIcon, TrendingDownIcon } from 'lucide-react';
import { Card, CardContent, Button } from '../ui';
import { budgetService } from '../../services/budgetService';
import type { Budget } from '../../types/budgets';

interface BudgetCardProps {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  onDelete: (budgetId: string) => void;
  isLoading?: boolean;
}

export function BudgetCard({ budget, onEdit, onDelete, isLoading = false }: BudgetCardProps) {
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const handleDelete = () => {
    if (showConfirmDelete) {
      onDelete(budget.id);
      setShowConfirmDelete(false);
    } else {
      setShowConfirmDelete(true);
    }
  };

  const handleCancelDelete = () => {
    setShowConfirmDelete(false);
  };

  const status = budgetService.getBudgetStatus(budget.usage);
  const statusColor = budgetService.getBudgetStatusColor(status);
  const statusBgColor = budgetService.getBudgetStatusBgColor(status);

  const percentageUsed = budget.usage?.percentage_used || 0;
  const progressWidth = Math.min(percentageUsed, 100);

  return (
    <Card className={`${isLoading ? 'opacity-50' : ''} transition-opacity`}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {budget.name}
              </h3>
              {budget.usage?.is_over_budget && (
                <AlertTriangleIcon className="h-4 w-4 text-red-500" />
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
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(budget)}
              disabled={isLoading}
              className="h-8 w-8 p-0"
            >
              <PencilIcon className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={showConfirmDelete ? handleCancelDelete : handleDelete}
              disabled={isLoading}
              className={`h-8 w-8 p-0 ${showConfirmDelete ? 'text-gray-500' : 'text-red-600 hover:text-red-700'}`}
            >
              {showConfirmDelete ? '✕' : <TrashIcon className="h-4 w-4" />}
            </Button>
            {showConfirmDelete && (
              <Button
                variant="danger"
                size="sm"
                onClick={handleDelete}
                disabled={isLoading}
                className="h-8 bg-red-600 hover:bg-red-700 text-white"
              >
                Confirm
              </Button>
            )}
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
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Progress
              </span>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {budgetService.formatPercentage(percentageUsed)}
              </span>
            </div>
            
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  budget.usage.is_over_budget
                    ? 'bg-red-500'
                    : percentageUsed >= 80
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${progressWidth}%` }}
              />
            </div>
          </div>
        )}

        {/* Spending Details */}
        {budget.usage && (
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <TrendingDownIcon className="h-4 w-4 text-red-500" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Spent
                </span>
              </div>
              <p className="text-sm font-semibold text-red-600">
                {budgetService.formatCurrency(budget.usage.spent_cents)}
              </p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <TrendingUpIcon className="h-4 w-4 text-green-500" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Remaining
                </span>
              </div>
              <p className={`text-sm font-semibold ${
                budget.usage.remaining_cents >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {budgetService.formatCurrency(budget.usage.remaining_cents)}
              </p>
            </div>
          </div>
        )}

        {/* Over Budget Warning */}
        {budget.usage?.is_over_budget && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center text-red-700 dark:text-red-400">
              <AlertTriangleIcon className="h-4 w-4 mr-2" />
              <span className="text-sm font-medium">
                Over budget by {budgetService.formatCurrency(budget.usage.spent_cents - budget.amount_cents)}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}