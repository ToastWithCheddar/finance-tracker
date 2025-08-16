import React, { useState } from 'react';
import { Plus, AlertCircle, Clock, DollarSign, Activity } from 'lucide-react';
import { 
  useRecurringSuggestions, 
  useRecurringRules, 
  useRecurringStats 
} from '../hooks/useRecurring';
import type { RecurringRuleFilter, PaginatedRecurringRulesResponse, RecurringRuleStats, RecurringSuggestion } from '../types/recurring';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { RecurringSuggestions } from '../components/recurring/RecurringSuggestions';
import { RecurringRulesList } from '../components/recurring/RecurringRulesList';
import { RecurringRuleForm } from '../components/recurring/RecurringRuleForm';
import { RecurringStatsCards } from '../components/recurring/RecurringStatsCards';
import { RecurringRulesFilters } from '../components/recurring/RecurringRulesFilters';
import { formatCurrency } from '../utils/currency';

// Type guard functions
const isRecurringRulesResponse = (data: any): data is PaginatedRecurringRulesResponse => {
  return data && typeof data === 'object' && Array.isArray(data.items);
};

const isRecurringStats = (data: any): data is RecurringRuleStats => {
  return data && typeof data === 'object' && typeof data.total_rules === 'number';
};

const isRecurringSuggestions = (data: any): data is RecurringSuggestion[] => {
  return Array.isArray(data);
};

export const Recurring: React.FC = () => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [filters, setFilters] = useState<RecurringRuleFilter>({});
  const [page, setPage] = useState(1);
  const [showInactiveRules, setShowInactiveRules] = useState(false);

  // Fetch data
  const { 
    data: suggestions, 
    isLoading: suggestionsLoading, 
    error: suggestionsError 
  } = useRecurringSuggestions();
  
  const { 
    data: rulesData, 
    isLoading: rulesLoading, 
    error: rulesError 
  } = useRecurringRules(
    page, 
    20, 
    { ...filters, is_active: showInactiveRules ? undefined : true }
  );
  
  const { 
    data: stats, 
    isLoading: statsLoading, 
    error: statsError 
  } = useRecurringStats();

  const handleFiltersChange = (newFilters: RecurringRuleFilter) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleClearFilters = () => {
    setFilters({});
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[hsl(var(--text))]">Recurring Transactions</h1>
          <p className="text-[hsl(var(--text))] opacity-70">
            Manage your subscriptions and recurring payments
          </p>
        </div>
        <Button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Rule
        </Button>
      </div>

      {/* Stats Cards */}
      {statsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <div className="p-4">
                <div className="animate-pulse">
                  <div className="flex items-center">
                    <div className="h-12 w-12 rounded-lg bg-gray-200 dark:bg-gray-700"></div>
                    <div className="ml-4 space-y-2">
                      <div className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
                      <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : statsError ? (
        <Card>
          <div className="p-4 text-center">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-500" />
            <p className="text-red-600 dark:text-red-400">Failed to load statistics</p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70 mt-1">
              {statsError.message || 'Please try refreshing the page'}
            </p>
          </div>
        </Card>
      ) : isRecurringStats(stats) ? (
        <RecurringStatsCards stats={stats} />
      ) : null}

      {/* Suggestions Section */}
      <Card>
        <CardHeader className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))]">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-orange-500 mr-2" />
            <CardTitle>Suggestions</CardTitle>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Found</span>
              <span className="px-2 py-1 text-xs font-medium rounded bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100">
                {isRecurringSuggestions(suggestions) ? suggestions.length : 0}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {suggestionsLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : suggestionsError ? (
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
              <p className="text-red-600 dark:text-red-400 mb-2">Failed to load suggestions</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">
                {suggestionsError.message || 'Please try refreshing the page'}
              </p>
            </div>
          ) : isRecurringSuggestions(suggestions) && suggestions.length > 0 ? (
            <RecurringSuggestions suggestions={suggestions} />
          ) : (
            <div className="text-center py-8">
              <Activity className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
              <p className="text-[hsl(var(--text))] opacity-80">No recurring transaction patterns detected.</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">
                Add more transactions or check back later for suggestions.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Rules Section */}
      <Card>
        <CardHeader className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))]">
          <div className="flex items-center">
            <Clock className="h-5 w-5 text-blue-500 mr-2" />
            <CardTitle>{showInactiveRules ? 'All Rules' : 'Active Rules'}</CardTitle>
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-6">
              {isRecurringRulesResponse(rulesData) && (
                <div className="flex items-center gap-2">
                  <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Total</span>
                  <span className="text-sm font-medium text-[hsl(var(--text))]">
                    {rulesData.total}
                  </span>
                </div>
              )}
              {isRecurringStats(stats) && (
                <>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Active</span>
                    <span className="text-sm font-medium text-[hsl(var(--text))]">{stats.active_rules}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Due week</span>
                    <span className="text-sm font-medium text-[hsl(var(--text))]">{stats.due_this_week}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Overdue</span>
                    <span className="text-sm font-medium text-[hsl(var(--text))]">{stats.overdue}</span>
                  </div>
                </>
              )}
            </div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={showInactiveRules}
                onChange={(e) => setShowInactiveRules(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-[hsl(var(--text))] opacity-70">Show inactive</span>
            </label>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {/* Filters */}
          <div className="mb-6">
            <RecurringRulesFilters
              filters={filters}
              onFiltersChange={handleFiltersChange}
              onClearFilters={handleClearFilters}
            />
          </div>

          {rulesLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : rulesError ? (
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
              <p className="text-red-600 dark:text-red-400 mb-2">Failed to load recurring rules</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">
                {rulesError.message || 'Please try refreshing the page'}
              </p>
            </div>
          ) : isRecurringRulesResponse(rulesData) && rulesData.items.length > 0 ? (
            <RecurringRulesList
              rules={rulesData.items}
              pagination={{
                page: rulesData.page,
                perPage: rulesData.per_page,
                total: rulesData.total,
                totalPages: rulesData.total_pages,
              }}
              onFiltersChange={handleFiltersChange}
              onPageChange={handlePageChange}
            />
          ) : (
            <div className="text-center py-8">
              <DollarSign className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
              <p className="text-[hsl(var(--text))] opacity-80">
                {Object.values(filters).some(v => v !== undefined && v !== '') 
                  ? 'No rules match your current filters.' 
                  : 'No recurring rules found.'
                }
              </p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">
                {Object.values(filters).some(v => v !== undefined && v !== '') 
                  ? 'Try adjusting your filters or clearing them to see all rules.'
                  : 'Create your first rule or approve a suggestion above.'
                }
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Monthly Summary */}
      {isRecurringRulesResponse(rulesData) && rulesData.total_monthly_amount_cents > 0 && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-2">
              Monthly Summary
            </h3>
            <div className="flex items-center justify-between">
              <span className="text-[hsl(var(--text))] opacity-70">
                Estimated total monthly recurring charges:
              </span>
              <span className="text-2xl font-bold text-red-600">
                {formatCurrency(rulesData.total_monthly_amount_cents / 100)}
              </span>
            </div>
            {rulesData.upcoming_in_week > 0 && (
              <div className="mt-3 pt-3 border-t border-[hsl(var(--border))]">
                <span className="text-sm text-orange-600">
                  {rulesData.upcoming_in_week} recurring payment(s) due in the next 7 days
                </span>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Create Rule Modal */}
      {showCreateForm && (
        <RecurringRuleForm
          isOpen={showCreateForm}
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => setShowCreateForm(false)}
        />
      )}
    </div>
  );
};