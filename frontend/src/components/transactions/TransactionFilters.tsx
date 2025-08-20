import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import type { TransactionFilters, TransactionGroupBy } from '../../types/transaction';
import { useSavedFilters, useSavedFilterOperations } from '../../hooks/useSavedFilters';
import type { SavedFilter } from '../../types/savedFilters';

interface TransactionFiltersProps {
  filters: TransactionFilters;
  onFiltersChange: (filters: TransactionFilters) => void;
  onClearFilters: () => void;
  categories?: string[];
}

interface SaveFilterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string) => void;
  isLoading?: boolean;
}

function SaveFilterModal({ isOpen, onClose, onSave, isLoading }: SaveFilterModalProps) {
  const [filterName, setFilterName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (filterName.trim()) {
      onSave(filterName.trim());
      setFilterName('');
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Save Filter">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Filter Name
          </label>
          <Input
            type="text"
            value={filterName}
            onChange={(e) => setFilterName(e.target.value)}
            placeholder="e.g., Monthly Groceries, Q1 Expenses..."
            className="w-full"
            required
          />
        </div>
        
        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!filterName.trim() || isLoading}>
            {isLoading ? 'Saving...' : 'Save Filter'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function TransactionFilters({ 
  filters, 
  onFiltersChange, 
  onClearFilters,
  categories = []
}: TransactionFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [currentSavedFilter, setCurrentSavedFilter] = useState<SavedFilter | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; filter?: SavedFilter }>({
    isOpen: false
  });
  
  // Saved filters hooks
  const { data: savedFilters, isLoading: isLoadingSavedFilters } = useSavedFilters();
  const savedFilterOperations = useSavedFilterOperations();

  const handleFilterChange = (key: keyof TransactionFilters, value: string | number | boolean | null) => {
    const newFilters = {
      ...filters,
      [key]: value || undefined, // Convert empty strings to undefined
    };
    onFiltersChange(newFilters);
    
    // Clear current saved filter if filters change
    if (currentSavedFilter) {
      setCurrentSavedFilter(null);
    }
  };

  // Check if current filters match a saved filter
  const matchingSavedFilter = savedFilters?.find(savedFilter => 
    JSON.stringify(savedFilter.filters) === JSON.stringify(filters)
  );

  // Check if current filters differ from empty state
  const hasUnsavedChanges = Object.values(filters).some(value => 
    value !== undefined && value !== '' && value !== null
  ) && !matchingSavedFilter;

  // Saved filter operations
  const handleApplySavedFilter = (savedFilter: SavedFilter) => {
    onFiltersChange(savedFilter.filters);
    setCurrentSavedFilter(savedFilter);
  };

  const handleSaveFilter = (name: string) => {
    savedFilterOperations.create({ name, filters });
  };

  const handleUpdateSavedFilter = () => {
    if (matchingSavedFilter) {
      savedFilterOperations.update({
        id: matchingSavedFilter.id,
        data: { filters }
      });
    }
  };

  const handleDeleteSavedFilter = (savedFilter: SavedFilter) => {
    setDeleteConfirm({ isOpen: true, filter: savedFilter });
  };

  const handleDeleteConfirm = () => {
    if (deleteConfirm.filter) {
      savedFilterOperations.delete(deleteConfirm.filter.id);
      if (currentSavedFilter?.id === deleteConfirm.filter.id) {
        setCurrentSavedFilter(null);
      }
    }
    setDeleteConfirm({ isOpen: false });
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
        {/* Search Bar and Saved Filters - Always Visible */}
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
          
          {/* Saved Filters Dropdown */}
          {savedFilters && savedFilters.length > 0 && (
            <div className="relative">
              <select
                value={matchingSavedFilter?.id || ''}
                onChange={(e) => {
                  const savedFilter = savedFilters.find(sf => sf.id === e.target.value);
                  if (savedFilter) {
                    handleApplySavedFilter(savedFilter);
                  }
                }}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              >
                <option value="">💾 Saved Filters</option>
                {savedFilters.map((savedFilter) => (
                  <option key={savedFilter.id} value={savedFilter.id}>
                    {savedFilter.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          
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
          
          {/* Save Filter Button */}
          {hasUnsavedChanges && (
            <Button
              variant="outline"
              onClick={() => setShowSaveModal(true)}
              disabled={savedFilterOperations.isCreating}
              className="text-green-600 border-green-300 hover:bg-green-50"
            >
              💾 Save Filter
            </Button>
          )}

          {/* Update/Delete Saved Filter Buttons */}
          {matchingSavedFilter && (
            <>
              <Button
                variant="outline"
                onClick={handleUpdateSavedFilter}
                disabled={savedFilterOperations.isUpdating}
                className="text-blue-600 border-blue-300 hover:bg-blue-50"
              >
                📝 Update
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDeleteSavedFilter(matchingSavedFilter)}
                disabled={savedFilterOperations.isDeleting}
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                🗑️ Delete
              </Button>
            </>
          )}

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
            {/* Group By Section */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Group By
              </label>
              <select
                value={filters.group_by || 'none'}
                onChange={(e) => handleFilterChange('group_by', e.target.value as TransactionGroupBy)}
                className="w-full md:w-auto px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="none">📋 No Grouping</option>
                <option value="date">📅 Group by Date</option>
                <option value="category">🏷️ Group by Category</option>
                <option value="merchant">🏪 Group by Merchant</option>
              </select>
            </div>
            
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
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
                  handleFilterChange('dateFrom', startOfMonth.toISOString().split('T')[0]);
                  handleFilterChange('dateTo', today.toISOString().split('T')[0]);
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
                  handleFilterChange('dateFrom', lastMonth.toISOString().split('T')[0]);
                  handleFilterChange('dateTo', endOfLastMonth.toISOString().split('T')[0]);
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
                  handleFilterChange('dateFrom', sevenDaysAgo.toISOString().split('T')[0]);
                  handleFilterChange('dateTo', today.toISOString().split('T')[0]);
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
                  handleFilterChange('dateFrom', thirtyDaysAgo.toISOString().split('T')[0]);
                  handleFilterChange('dateTo', today.toISOString().split('T')[0]);
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

              {/* New Smart Preset Buttons */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onFiltersChange({
                    ...filters,
                    amountMinCents: 10000, // $100 in cents
                    transaction_type: 'expense'
                  });
                  // Clear current saved filter since filters changed
                  if (currentSavedFilter) {
                    setCurrentSavedFilter(null);
                  }
                }}
              >
                💳 Large Expenses
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
                  onFiltersChange({
                    ...filters,
                    dateFrom: startOfMonth.toISOString().split('T')[0],
                    dateTo: today.toISOString().split('T')[0],
                    search: 'dining food restaurant'
                  });
                  // Clear current saved filter since filters changed
                  if (currentSavedFilter) {
                    setCurrentSavedFilter(null);
                  }
                }}
              >
                🍽️ This Month's Dining
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onFiltersChange({
                    ...filters,
                    categoryId: '__uncategorized__' // Special value to indicate null categories
                  });
                  // Clear current saved filter since filters changed
                  if (currentSavedFilter) {
                    setCurrentSavedFilter(null);
                  }
                }}
              >
                📝 Uncategorized
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

        {/* Delete Filter Confirmation Modal */}
        <Modal
          isOpen={deleteConfirm.isOpen}
          onClose={() => setDeleteConfirm({ isOpen: false })}
          title="Delete Saved Filter"
        >
          <div className="space-y-4">
            <p>
              Are you sure you want to delete the saved filter "<strong>{deleteConfirm.filter?.name}</strong>"?
            </p>
            <p className="text-sm text-[hsl(var(--text))/0.75]">
              This action cannot be undone. You will need to recreate the filter if you need it again.
            </p>
            
            <div className="flex justify-end space-x-3">
              <Button
                variant="outline"
                onClick={() => setDeleteConfirm({ isOpen: false })}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleDeleteConfirm}
                className="bg-red-600 hover:bg-red-700"
              >
                Delete Filter
              </Button>
            </div>
          </div>
        </Modal>

        {/* Save Filter Modal */}
        <SaveFilterModal
          isOpen={showSaveModal}
          onClose={() => setShowSaveModal(false)}
          onSave={handleSaveFilter}
          isLoading={savedFilterOperations.isCreating}
        />
      </div>
    </Card>
  );
}