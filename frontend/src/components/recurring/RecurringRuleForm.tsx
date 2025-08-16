import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { RecurringTransactionRuleCreate } from '../../types/recurring';
import { useCreateRecurringRule } from '../../hooks/useRecurring';
import { useAccounts } from '../../hooks/useAccounts';
import { categoryService } from '../../services/categoryService';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import type { CategoryWithChildren } from '../../types/category';

interface RecurringRuleFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const RecurringRuleForm: React.FC<RecurringRuleFormProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const createRule = useCreateRecurringRule();
  const { data: accounts } = useAccounts();
  const [categories, setCategories] = useState<CategoryWithChildren[]>([]);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    amount_dollars: '',
    account_id: '',
    category_id: '',
    frequency: 'monthly' as const,
    interval: 1,
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    tolerance_dollars: '5.00',
    auto_categorize: true,
    generate_notifications: true,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const categoriesData = await categoryService.getCategoriesHierarchy();
        setCategories(categoriesData);
      } catch (error) {
        console.error('Failed to load categories:', error);
      }
    };

    if (isOpen) {
      loadCategories();
    }
  }, [isOpen]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    if (!formData.amount_dollars || parseFloat(formData.amount_dollars) <= 0) {
      newErrors.amount_dollars = 'Amount must be greater than 0';
    }

    if (!formData.account_id) {
      newErrors.account_id = 'Account is required';
    }

    if (!formData.start_date) {
      newErrors.start_date = 'Start date is required';
    }

    if (formData.end_date && formData.end_date <= formData.start_date) {
      newErrors.end_date = 'End date must be after start date';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const ruleData: RecurringTransactionRuleCreate = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      amount_cents: Math.round(parseFloat(formData.amount_dollars) * 100),
      currency: 'USD',
      account_id: formData.account_id,
      category_id: formData.category_id || undefined,
      frequency: formData.frequency,
      interval: formData.interval,
      start_date: formData.start_date,
      end_date: formData.end_date || undefined,
      tolerance_cents: Math.round(parseFloat(formData.tolerance_dollars) * 100),
      auto_categorize: formData.auto_categorize,
      generate_notifications: formData.generate_notifications,
    };

    createRule.mutate(ruleData, {
      onSuccess: () => {
        onSuccess();
        setFormData({
          name: '',
          description: '',
          amount_dollars: '',
          account_id: '',
          category_id: '',
          frequency: 'monthly',
          interval: 1,
          start_date: new Date().toISOString().split('T')[0],
          end_date: '',
          tolerance_dollars: '5.00',
          auto_categorize: true,
          generate_notifications: true,
        });
        setErrors({});
      },
    });
  };

  const handleChange = (field: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-[hsl(var(--text))]">
            Create Recurring Rule
          </h2>
          <button
            onClick={onClose}
            className="text-[hsl(var(--text))] opacity-60 hover:opacity-100"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Rule Name *
              </label>
              <Input
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="e.g., Netflix Subscription"
                error={errors.name}
              />
            </div>

            {/* Account */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Account *
              </label>
              <select
                value={formData.account_id}
                onChange={(e) => handleChange('account_id', e.target.value)}
                className={`w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border ${
                  errors.account_id ? 'border-red-300' : 'border-[hsl(var(--border))]'
                }`}
              >
                <option value="">Select account...</option>
                {accounts?.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
              {errors.account_id && (
                <p className="mt-1 text-sm text-red-600">{errors.account_id}</p>
              )}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
              Description *
            </label>
            <Input
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="e.g., NETFLIX.COM"
              error={errors.description}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Amount */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Amount ($) *
              </label>
              <Input
                type="number"
                step="0.01"
                value={formData.amount_dollars}
                onChange={(e) => handleChange('amount_dollars', e.target.value)}
                placeholder="12.99"
                error={errors.amount_dollars}
              />
            </div>

            {/* Frequency */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Frequency
              </label>
              <select
                value={formData.frequency}
                onChange={(e) => handleChange('frequency', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                <option value="weekly">Weekly</option>
                <option value="biweekly">Bi-weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annually">Annually</option>
              </select>
            </div>

            {/* Interval */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Every X periods
              </label>
              <Input
                type="number"
                min="1"
                max="12"
                value={formData.interval}
                onChange={(e) => handleChange('interval', parseInt(e.target.value))}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Start Date */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Start Date *
              </label>
              <Input
                type="date"
                value={formData.start_date}
                onChange={(e) => handleChange('start_date', e.target.value)}
                error={errors.start_date}
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                End Date (optional)
              </label>
              <Input
                type="date"
                value={formData.end_date}
                onChange={(e) => handleChange('end_date', e.target.value)}
                error={errors.end_date}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Category */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Category (optional)
              </label>
              <select
                value={formData.category_id}
                onChange={(e) => handleChange('category_id', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                <option value="">Select category...</option>
                {categories?.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.emoji} {category.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Tolerance */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Amount Tolerance ($)
              </label>
              <Input
                type="number"
                step="0.01"
                value={formData.tolerance_dollars}
                onChange={(e) => handleChange('tolerance_dollars', e.target.value)}
                placeholder="5.00"
              />
            </div>
          </div>

          {/* Checkboxes */}
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.auto_categorize}
                onChange={(e) => handleChange('auto_categorize', e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-[hsl(var(--text))] opacity-80">
                Automatically categorize matching transactions
              </span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.generate_notifications}
                onChange={(e) => handleChange('generate_notifications', e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-[hsl(var(--text))] opacity-80">
                Send notifications for upcoming payments
              </span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createRule.isPending}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {createRule.isPending ? 'Creating...' : 'Create Rule'}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
};