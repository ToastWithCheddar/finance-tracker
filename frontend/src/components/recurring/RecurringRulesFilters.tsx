import React, { useState, useEffect } from 'react';
import { Search, Filter, X, Calendar, DollarSign, Activity } from 'lucide-react';
import type { RecurringRuleFilter } from '../../types/recurring';
import { useAccounts } from '../../hooks/useAccounts';
import { categoryService } from '../../services/categoryService';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import type { CategoryWithChildren } from '../../types/category';

interface RecurringRulesFiltersProps {
  filters: RecurringRuleFilter;
  onFiltersChange: (filters: RecurringRuleFilter) => void;
  onClearFilters: () => void;
}

export const RecurringRulesFilters: React.FC<RecurringRulesFiltersProps> = ({
  filters,
  onFiltersChange,
  onClearFilters,
}) => {
  const { data: accounts } = useAccounts();
  const [categories, setCategories] = useState<CategoryWithChildren[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const categoriesData = await categoryService.getCategoriesHierarchy();
        setCategories(categoriesData);
      } catch (error) {
        console.error('Failed to load categories:', error);
      }
    };

    loadCategories();
  }, []);

  // Check if any advanced filters are active
  const hasAdvancedFilters = !!(
    filters.frequency ||
    filters.account_id ||
    filters.category_id ||
    filters.next_due_from ||
    filters.next_due_to ||
    filters.min_amount_cents ||
    filters.max_amount_cents ||
    filters.is_confirmed !== undefined
  );

  useEffect(() => {
    if (hasAdvancedFilters) {
      setShowAdvanced(true);
    }
  }, [hasAdvancedFilters]);

  const handleFilterChange = (key: keyof RecurringRuleFilter, value: string | boolean | number | undefined) => {
    onFiltersChange({
      ...filters,
      [key]: value === '' ? undefined : value,
    });
  };

  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '').length;

  return (
    <div className="space-y-4">
      {/* Basic Filters */}
      <div className="flex items-center space-x-4">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[hsl(var(--text))] opacity-50" />
          <Input
            placeholder="Search by name or description..."
            value={filters.search || ''}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Active Status Filter */}
        <div className="flex items-center space-x-2">
          <Activity className="h-4 w-4 text-[hsl(var(--text))] opacity-70" />
          <select
            value={filters.is_active === undefined ? 'all' : filters.is_active.toString()}
            onChange={(e) => 
              handleFilterChange('is_active', e.target.value === 'all' ? undefined : e.target.value === 'true')
            }
            className="px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
          >
            <option value="all">All Rules</option>
            <option value="true">Active Only</option>
            <option value="false">Inactive Only</option>
          </select>
        </div>

        {/* Advanced Filters Toggle */}
        <Button
          onClick={() => setShowAdvanced(!showAdvanced)}
          variant="outline"
          size="sm"
          className={`${hasAdvancedFilters ? 'border-blue-300 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20' : ''}`}
        >
          <Filter className="h-4 w-4 mr-2" />
          Advanced
          {activeFilterCount > 0 && (
            <span className="ml-2 px-2 py-1 text-xs rounded-full bg-blue-600 text-white">
              {activeFilterCount}
            </span>
          )}
        </Button>

        {/* Clear Filters */}
        {activeFilterCount > 0 && (
          <Button
            onClick={onClearFilters}
            variant="outline"
            size="sm"
            className="text-red-600 hover:text-red-800 dark:text-red-300 dark:hover:text-red-200"
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="border border-[hsl(var(--border))] rounded-lg p-4 bg-[hsl(var(--surface))]">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Frequency Filter */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Frequency
              </label>
              <select
                value={filters.frequency || ''}
                onChange={(e) => handleFilterChange('frequency', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                <option value="">All Frequencies</option>
                <option value="weekly">Weekly</option>
                <option value="biweekly">Bi-weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annually">Annually</option>
              </select>
            </div>

            {/* Account Filter */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Account
              </label>
              <select
                value={filters.account_id || ''}
                onChange={(e) => handleFilterChange('account_id', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                <option value="">All Accounts</option>
                {accounts?.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Category Filter */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Category
              </label>
              <select
                value={filters.category_id || ''}
                onChange={(e) => handleFilterChange('category_id', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                <option value="">All Categories</option>
                {categories?.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.emoji} {category.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Confirmation Status */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Source
              </label>
              <select
                value={filters.is_confirmed === undefined ? 'all' : filters.is_confirmed.toString()}
                onChange={(e) => 
                  handleFilterChange('is_confirmed', e.target.value === 'all' ? undefined : e.target.value === 'true')
                }
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                <option value="all">All Sources</option>
                <option value="true">User Created</option>
                <option value="false">AI Suggested</option>
              </select>
            </div>

            {/* Date Range Filters */}
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                <Calendar className="inline h-4 w-4 mr-1" />
                Next Due From
              </label>
              <Input
                type="date"
                value={filters.next_due_from || ''}
                onChange={(e) => handleFilterChange('next_due_from', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                <Calendar className="inline h-4 w-4 mr-1" />
                Next Due To
              </label>
              <Input
                type="date"
                value={filters.next_due_to || ''}
                onChange={(e) => handleFilterChange('next_due_to', e.target.value)}
              />
            </div>
          </div>

          {/* Amount Range Filters */}
          <div className="mt-4">
            <label className="block text-sm font-medium mb-2 text-[hsl(var(--text))] opacity-80">
              <DollarSign className="inline h-4 w-4 mr-1" />
              Amount Range
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs mb-1 text-[hsl(var(--text))] opacity-60">
                  Minimum Amount ($)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={filters.min_amount_cents ? (filters.min_amount_cents / 100).toString() : ''}
                  onChange={(e) => 
                    handleFilterChange('min_amount_cents', e.target.value ? Math.round(parseFloat(e.target.value) * 100) : undefined)
                  }
                />
              </div>
              <div>
                <label className="block text-xs mb-1 text-[hsl(var(--text))] opacity-60">
                  Maximum Amount ($)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="999.99"
                  value={filters.max_amount_cents ? (filters.max_amount_cents / 100).toString() : ''}
                  onChange={(e) => 
                    handleFilterChange('max_amount_cents', e.target.value ? Math.round(parseFloat(e.target.value) * 100) : undefined)
                  }
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};