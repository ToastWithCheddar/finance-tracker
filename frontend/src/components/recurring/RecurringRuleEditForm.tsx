import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { RecurringTransactionRule, RecurringTransactionRuleUpdate } from '../../types/recurring';
import { useUpdateRecurringRule } from '../../hooks/useRecurring';
import { useAccounts } from '../../hooks/useAccounts';
import { categoryService } from '../../services/categoryService';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import type { CategoryWithChildren } from '../../types/category';

interface RecurringRuleEditFormProps {
  isOpen: boolean;
  onClose: () => void;
  rule: RecurringTransactionRule | null;
}

export const RecurringRuleEditForm: React.FC<RecurringRuleEditFormProps> = ({
  isOpen,
  onClose,
  rule,
}) => {
  const updateRule = useUpdateRecurringRule();
  const { data: accounts } = useAccounts();
  const [categories, setCategories] = useState<CategoryWithChildren[]>([]);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    amount_dollars: '',
    frequency: 'monthly' as const,
    interval: 1,
    end_date: '',
    tolerance_dollars: '5.00',
    auto_categorize: true,
    generate_notifications: true,
    is_active: true,
    category_id: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Populate form when rule changes
  useEffect(() => {
    if (rule) {
      setFormData({
        name: rule.name,
        description: rule.description,
        amount_dollars: rule.amount_dollars.toString(),
        frequency: rule.frequency,
        interval: rule.interval,
        end_date: rule.end_date || '',
        tolerance_dollars: (rule.tolerance_cents / 100).toString(),
        auto_categorize: rule.auto_categorize,
        generate_notifications: rule.generate_notifications,
        is_active: rule.is_active,
        category_id: rule.category_id || '',
      });
    }
  }, [rule]);

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

    if (formData.end_date && rule && formData.end_date <= rule.start_date) {
      newErrors.end_date = 'End date must be after start date';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!rule || !validateForm()) {
      return;
    }

    const updateData: RecurringTransactionRuleUpdate = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      amount_cents: Math.round(parseFloat(formData.amount_dollars) * 100),
      frequency: formData.frequency,
      interval: formData.interval,
      end_date: formData.end_date || null,
      tolerance_cents: Math.round(parseFloat(formData.tolerance_dollars) * 100),
      auto_categorize: formData.auto_categorize,
      generate_notifications: formData.generate_notifications,
      is_active: formData.is_active,
      category_id: formData.category_id || undefined,
    };

    updateRule.mutate(
      { id: rule.id, updates: updateData },
      {
        onSuccess: () => {
          onClose();
          setErrors({});
        },
      }
    );
  };

  const handleChange = (field: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  if (!rule) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-[hsl(var(--text))]">
            Edit Recurring Rule
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

            {/* Account (Read-only for editing) */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Account
              </label>
              <div className="px-3 py-2 bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-md text-[hsl(var(--text))] opacity-60">
                {accounts?.find(a => a.id === rule.account_id)?.name || 'Unknown Account'}
              </div>
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

          {/* Checkboxes */}
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => handleChange('is_active', e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-[hsl(var(--text))] opacity-80">
                Rule is active
              </span>
            </label>

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
              disabled={updateRule.isPending}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {updateRule.isPending ? 'Updating...' : 'Update Rule'}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
};