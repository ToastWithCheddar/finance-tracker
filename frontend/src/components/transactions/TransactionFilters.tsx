import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { getYesterday, getThisWeekRange } from '../../utils/date';
import type { TransactionFilters } from '../../types/transaction';

interface TransactionFiltersProps {
  filters: TransactionFilters;
  onFiltersChange: (filters: TransactionFilters) => void;
  onClearFilters: () => void;
  categories?: string[];
}


export function TransactionFilters({ 
  filters, 
  onFiltersChange, 
  onClearFilters,
  categories = []
}: TransactionFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleFilterChange = (key: keyof TransactionFilters, value: string | number | boolean | null | undefined) => {
    const newFilters = {
      ...filters,
      [key]: value || undefined, // Convert empty strings to undefined
    };
    console.log('🔍 [TransactionFilters] Filter changed:', { key, value, newFilters });
    onFiltersChange(newFilters);
  };

  // Handle multiple filter changes atomically to prevent race conditions
  const handleMultipleFilterChanges = (updates: Partial<TransactionFilters>) => {
    const newFilters = {
      ...filters,
      ...updates,
    };
    // Clean up undefined values
    Object.keys(newFilters).forEach(key => {
      if (newFilters[key as keyof TransactionFilters] === undefined || newFilters[key as keyof TransactionFilters] === '') {
        delete newFilters[key as keyof TransactionFilters];
      }
    });
    console.log('🔍 [TransactionFilters] Multiple filters changed:', { updates, newFilters });
    onFiltersChange(newFilters);
  };

  // Helper functions to check if specific quick filters are active
  const isQuickFilterActive = (quickFilterType: string): boolean => {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    
    switch (quickFilterType) {
      case 'yesterday': {
        const yesterday = getYesterday();
        return filters.dateFrom === yesterday && filters.dateTo === yesterday;
      }
      case 'thisWeek': {
        const { startDate, endDate } = getThisWeekRange();
        return filters.dateFrom === startDate && filters.dateTo === endDate;
      }
      case 'thisMonth': {
        const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        const startOfMonthStr = startOfMonth.toISOString().split('T')[0];
        return filters.dateFrom === startOfMonthStr && filters.dateTo === todayStr;
      }
      case 'lastMonth': {
        const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
        return filters.dateFrom === lastMonth.toISOString().split('T')[0] && 
               filters.dateTo === endOfLastMonth.toISOString().split('T')[0];
      }
      case 'last7Days': {
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(today.getDate() - 7);
        return filters.dateFrom === sevenDaysAgo.toISOString().split('T')[0] && 
               filters.dateTo === todayStr;
      }
      case 'last30Days': {
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(today.getDate() - 30);
        return filters.dateFrom === thirtyDaysAgo.toISOString().split('T')[0] && 
               filters.dateTo === todayStr;
      }
      case 'incomeOnly':
        return filters.transaction_type === 'income';
      case 'expenseOnly':
        return filters.transaction_type === 'expense';
      default:
        return false;
    }
  };


  const hasActiveFilters = Object.values(filters).some(value => 
    value !== undefined && value !== '' && value !== null
  );

  const filterCount = Object.values(filters).filter(value => 
    value !== undefined && value !== '' && value !== null
  ).length;

  return (
    <Card>
      <div className="p-4">
        {/* Search Bar - Always Visible */}
        <div className="flex items-center space-x-4 mb-4">
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-400">🔍</span>
              </div>
              <Input
                type="text"
                placeholder="Search description, merchant, category, notes..."
                value={filters.search || ''}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                className="pl-10 pr-10"
                title="Search across transaction description, merchant, category names, and notes"
              />
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <span className="text-gray-400 text-xs" title="Smart search across all transaction fields">
                  💡
                </span>
              </div>
            </div>
          </div>
          
          
          <Button
            variant="outline"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center space-x-2"
          >
            <span>Filters</span>
            {filterCount > 0 && (
              <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded-full">
                {filterCount}
              </span>
            )}
            <span className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
              ▼
            </span>
          </Button>

          {hasActiveFilters && (
            <Button
              variant="outline"
              onClick={onClearFilters}
              className="text-red-600 border-red-300 hover:bg-red-50"
            >
              Clear All
            </Button>
          )}
        </div>

        {/* Advanced Filters - Collapsible */}
        {isExpanded && (
          <div className="space-y-4 pt-4 border-t border-gray-200">
            {/* Removed: Group By Section - using flat transaction list now */}
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Date
                </label>
                <Input
                  type="date"
                  value={filters.dateFrom || ''}
                  onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Date
                </label>
                <Input
                  type="date"
                  value={filters.dateTo || ''}
                  onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                />
              </div>

              {/* Transaction Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Transaction Type
                </label>
                <select
                  value={filters.transaction_type || ''}
                  onChange={(e) => handleFilterChange('transaction_type', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All Types</option>
                  <option value="income">💰 Income</option>
                  <option value="expense">💸 Expense</option>
                </select>
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category
                </label>
                <select
                  value={filters.categoryId || ''}
                  onChange={(e) => handleFilterChange('categoryId', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All Categories</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              {/* Amount Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Min Amount
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={filters.amountMinCents ? (filters.amountMinCents / 100).toString() : ''}
                  onChange={(e) => {
                    const dollars = parseFloat(e.target.value);
                    handleFilterChange('amountMinCents', dollars ? Math.round(dollars * 100) : undefined);
                  }}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Amount
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={filters.amountMaxCents ? (filters.amountMaxCents / 100).toString() : ''}
                  onChange={(e) => {
                    const dollars = parseFloat(e.target.value);
                    handleFilterChange('amountMaxCents', dollars ? Math.round(dollars * 100) : undefined);
                  }}
                />
              </div>
            </div>

            {/* Quick Filter Buttons */}
            <div className="flex flex-wrap gap-2 pt-4 border-t border-gray-100">
              <span className="text-sm font-medium text-gray-700 mr-2">Quick filters:</span>
              
              <Button
                variant={isQuickFilterActive('yesterday') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  const yesterday = getYesterday();
                  handleMultipleFilterChanges({
                    dateFrom: yesterday,
                    dateTo: yesterday,
                    // Clear transaction type when setting date range
                    transaction_type: undefined
                  });
                }}
              >
                Yesterday
              </Button>
              
              <Button
                variant={isQuickFilterActive('thisWeek') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  const { startDate, endDate } = getThisWeekRange();
                  handleMultipleFilterChanges({
                    dateFrom: startDate,
                    dateTo: endDate,
                    // Clear transaction type when setting date range
                    transaction_type: undefined
                  });
                }}
              >
                This Week
              </Button>
              
              <Button
                variant={isQuickFilterActive('thisMonth') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
                  handleMultipleFilterChanges({
                    dateFrom: startOfMonth.toISOString().split('T')[0],
                    dateTo: today.toISOString().split('T')[0],
                    // Clear transaction type when setting date range
                    transaction_type: undefined
                  });
                }}
              >
                This Month
              </Button>
              
              <Button
                variant={isQuickFilterActive('lastMonth') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                  const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
                  handleMultipleFilterChanges({
                    dateFrom: lastMonth.toISOString().split('T')[0],
                    dateTo: endOfLastMonth.toISOString().split('T')[0],
                    // Clear transaction type when setting date range
                    transaction_type: undefined
                  });
                }}
              >
                Last Month
              </Button>
              
              <Button
                variant={isQuickFilterActive('last7Days') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const sevenDaysAgo = new Date(today);
                  sevenDaysAgo.setDate(today.getDate() - 7);
                  handleMultipleFilterChanges({
                    dateFrom: sevenDaysAgo.toISOString().split('T')[0],
                    dateTo: today.toISOString().split('T')[0],
                    // Clear transaction type when setting date range
                    transaction_type: undefined
                  });
                }}
              >
                Last 7 Days
              </Button>
              
              <Button
                variant={isQuickFilterActive('last30Days') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const thirtyDaysAgo = new Date(today);
                  thirtyDaysAgo.setDate(today.getDate() - 30);
                  handleMultipleFilterChanges({
                    dateFrom: thirtyDaysAgo.toISOString().split('T')[0],
                    dateTo: today.toISOString().split('T')[0],
                    // Clear transaction type when setting date range
                    transaction_type: undefined
                  });
                }}
              >
                Last 30 Days
              </Button>

              <Button
                variant={isQuickFilterActive('incomeOnly') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  handleMultipleFilterChanges({
                    transaction_type: 'income',
                    // Clear date filters when setting transaction type
                    dateFrom: undefined,
                    dateTo: undefined
                  });
                }}
              >
                💰 Income Only
              </Button>

              <Button
                variant={isQuickFilterActive('expenseOnly') ? 'primary' : 'outline'}
                size="sm"
                onClick={() => {
                  handleMultipleFilterChanges({
                    transaction_type: 'expense',
                    // Clear date filters when setting transaction type
                    dateFrom: undefined,
                    dateTo: undefined
                  });
                }}
              >
                💸 Expenses Only
              </Button>

            </div>
          </div>
        )}

        {/* Active Filters Display */}
        {hasActiveFilters && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center space-x-2 flex-wrap">
              <span className="text-sm font-medium text-gray-700">Active filters:</span>
              
              {filters.search && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Search: "{filters.search}"
                  <button
                    onClick={() => handleFilterChange('search', '')}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
              
              {filters.transaction_type && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Type: {filters.transaction_type === 'income' ? '💰 Income' : '💸 Expense'}
                  <button
                    onClick={() => handleFilterChange('transaction_type', '')}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
              
              {filters.categoryId && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Category: {categories.find(cat => cat === filters.categoryId) || filters.categoryId}
                  <button
                    onClick={() => handleFilterChange('categoryId', '')}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
              
              {(filters.dateFrom || filters.dateTo) && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Date: {filters.dateFrom || '...'} to {filters.dateTo || '...'}
                  <button
                    onClick={() => {
                      handleFilterChange('dateFrom', '');
                      handleFilterChange('dateTo', '');
                    }}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
              
              {(filters.amountMinCents !== undefined || filters.amountMaxCents !== undefined) && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Amount: ${filters.amountMinCents ? (filters.amountMinCents / 100) : 0} - ${filters.amountMaxCents ? (filters.amountMaxCents / 100) : '∞'}
                  <button
                    onClick={() => {
                      handleFilterChange('amountMinCents', undefined);
                      handleFilterChange('amountMaxCents', undefined);
                    }}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
          </div>
        )}

      </div>
    </Card>
  );
}