import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import type { TransactionFilter } from '../../types/transactions';

interface TransactionFiltersProps {
  filters: TransactionFilter;
  onFiltersChange: (filters: TransactionFilter) => void;
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

  const handleFilterChange = (key: keyof TransactionFilter, value: string | number | boolean | null) => {
    onFiltersChange({
      ...filters,
      [key]: value || undefined, // Convert empty strings to undefined
    });
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
                placeholder="Search transactions..."
                value={filters.search_query || ''}
                onChange={(e) => handleFilterChange('search_query', e.target.value)}
                className="pl-10"
              />
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Date
                </label>
                <Input
                  type="date"
                  value={filters.start_date || ''}
                  onChange={(e) => handleFilterChange('start_date', e.target.value)}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Date
                </label>
                <Input
                  type="date"
                  value={filters.end_date || ''}
                  onChange={(e) => handleFilterChange('end_date', e.target.value)}
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
                  value={filters.category || ''}
                  onChange={(e) => handleFilterChange('category', e.target.value)}
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
                  value={filters.min_amount || ''}
                  onChange={(e) => handleFilterChange('min_amount', parseFloat(e.target.value) || undefined)}
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
                  value={filters.max_amount || ''}
                  onChange={(e) => handleFilterChange('max_amount', parseFloat(e.target.value) || undefined)}
                />
              </div>
            </div>

            {/* Quick Filter Buttons */}
            <div className="flex flex-wrap gap-2 pt-4 border-t border-gray-100">
              <span className="text-sm font-medium text-gray-700 mr-2">Quick filters:</span>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
                  handleFilterChange('start_date', startOfMonth.toISOString().split('T')[0]);
                  handleFilterChange('end_date', today.toISOString().split('T')[0]);
                }}
              >
                This Month
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                  const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
                  handleFilterChange('start_date', lastMonth.toISOString().split('T')[0]);
                  handleFilterChange('end_date', endOfLastMonth.toISOString().split('T')[0]);
                }}
              >
                Last Month
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const sevenDaysAgo = new Date(today);
                  sevenDaysAgo.setDate(today.getDate() - 7);
                  handleFilterChange('start_date', sevenDaysAgo.toISOString().split('T')[0]);
                  handleFilterChange('end_date', today.toISOString().split('T')[0]);
                }}
              >
                Last 7 Days
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const thirtyDaysAgo = new Date(today);
                  thirtyDaysAgo.setDate(today.getDate() - 30);
                  handleFilterChange('start_date', thirtyDaysAgo.toISOString().split('T')[0]);
                  handleFilterChange('end_date', today.toISOString().split('T')[0]);
                }}
              >
                Last 30 Days
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleFilterChange('transaction_type', 'income')}
              >
                💰 Income Only
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleFilterChange('transaction_type', 'expense')}
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
              
              {filters.search_query && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Search: "{filters.search_query}"
                  <button
                    onClick={() => handleFilterChange('search_query', '')}
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
              
              {filters.category && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Category: {filters.category}
                  <button
                    onClick={() => handleFilterChange('category', '')}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
              
              {(filters.start_date || filters.end_date) && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Date: {filters.start_date || '...'} to {filters.end_date || '...'}
                  <button
                    onClick={() => {
                      handleFilterChange('start_date', '');
                      handleFilterChange('end_date', '');
                    }}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              )}
              
              {(filters.min_amount !== undefined || filters.max_amount !== undefined) && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Amount: ${filters.min_amount || 0} - ${filters.max_amount || '∞'}
                  <button
                    onClick={() => {
                      handleFilterChange('min_amount', undefined);
                      handleFilterChange('max_amount', undefined);
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