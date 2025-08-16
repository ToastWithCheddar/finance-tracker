import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { X } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { budgetService } from '../../services/budgetService';
import { 
  BudgetPeriod, 
  type Budget, 
  type CreateBudgetRequest, 
  type UpdateBudgetRequest 
} from '../../types/budgets';

interface Category {
  id: string;
  name: string;
  emoji?: string;
}

interface BudgetFormProps {
  budget?: Budget;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateBudgetRequest | UpdateBudgetRequest) => void;
  isLoading?: boolean;
}

export function BudgetForm({ budget, isOpen, onClose, onSubmit, isLoading = false }: BudgetFormProps) {
  const isEditing = !!budget;
  const [amountInput, setAmountInput] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<CreateBudgetRequest>();

  // Get categories for the dropdown
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => apiClient.get<Category[]>('/categories'),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Reset form when budget changes or modal opens
  useEffect(() => {
    if (isOpen) {
      if (budget) {
        // Edit mode - populate form with budget data
        reset({
          name: budget.name,
          category_id: budget.category_id || '',
          amount_cents: budget.amount_cents,
          period: budget.period,
          start_date: budget.start_date,
          end_date: budget.end_date || '',
          alert_threshold: budget.alert_threshold,
          is_active: budget.is_active,
        });
        setAmountInput((budget.amount_cents / 100).toString());
      } else {
        // Create mode - reset to defaults
        reset({
          name: '',
          category_id: '',
          amount_cents: 0,
          period: BudgetPeriod.MONTHLY,
          start_date: new Date().toISOString().split('T')[0],
          end_date: '',
          alert_threshold: 0.8,
          is_active: true,
        });
        setAmountInput('');
      }
    }
  }, [budget, isOpen, reset]);

  // Handle amount input changes
  const handleAmountChange = (value: string) => {
    setAmountInput(value);
    const numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      setValue('amount_cents', Math.round(numericValue * 100));
    }
  };

  const onFormSubmit = (data: CreateBudgetRequest) => {
    // Clean up the data
    const cleanData = {
      ...data,
      category_id: data.category_id || undefined,
      end_date: data.end_date || undefined,
    };

    onSubmit(cleanData);
  };

  const watchedPeriod = watch('period');

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {isEditing ? 'Edit Budget' : 'Create New Budget'}
            </CardTitle>
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
        
        <CardContent>
          <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
            {/* Budget Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Budget Name
              </label>
              <Input
                id="name"
                {...register('name', { 
                  required: 'Budget name is required',
                  minLength: { value: 1, message: 'Budget name cannot be empty' }
                })}
                placeholder="e.g., Monthly Groceries, Entertainment Budget"
                disabled={isLoading}
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
              )}
            </div>

            {/* Category Selection */}
            <div>
              <label htmlFor="category_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Category (Optional)
              </label>
              <select
                id="category_id"
                {...register('category_id')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                disabled={isLoading}
              >
                <option value="">All Categories</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.emoji ? `${category.emoji} ${category.name}` : category.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Budget Amount */}
            <div>
              <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Budget Amount
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400">
                  $
                </span>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={amountInput}
                  onChange={(e) => handleAmountChange(e.target.value)}
                  className="pl-8"
                  placeholder="0.00"
                  disabled={isLoading}
                />
              </div>
              {errors.amount_cents && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">Amount must be greater than 0</p>
              )}
            </div>

            {/* Period Selection */}
            <div>
              <label htmlFor="period" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Budget Period
              </label>
              <select
                id="period"
                {...register('period', { required: 'Please select a period' })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                disabled={isLoading}
              >
                {Object.values(BudgetPeriod).map((period) => (
                  <option key={period} value={period}>
                    {budgetService.getPeriodDisplayName(period)}
                  </option>
                ))}
              </select>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="start_date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Start Date
                </label>
                <Input
                  id="start_date"
                  type="date"
                  {...register('start_date', { required: 'Start date is required' })}
                  disabled={isLoading}
                />
                {errors.start_date && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.start_date.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="end_date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  End Date (Optional)
                </label>
                <Input
                  id="end_date"
                  type="date"
                  {...register('end_date')}
                  disabled={isLoading}
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Leave empty for recurring {watchedPeriod} budget
                </p>
              </div>
            </div>

            {/* Alert Threshold */}
            <div>
              <label htmlFor="alert_threshold" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Alert Threshold ({Math.round((watch('alert_threshold') || 0.8) * 100)}%)
              </label>
              <input
                id="alert_threshold"
                type="range"
                min="0.1"
                max="1.0"
                step="0.1"
                {...register('alert_threshold')}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                disabled={isLoading}
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                <span>10%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Active Status */}
            <div className="flex items-center">
              <input
                id="is_active"
                type="checkbox"
                {...register('is_active')}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
                disabled={isLoading}
              />
              <label htmlFor="is_active" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                Budget is active
              </label>
            </div>

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-600">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isLoading}
              >
                {isLoading ? 'Saving...' : isEditing ? 'Update Budget' : 'Create Budget'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </Modal>
  );
}