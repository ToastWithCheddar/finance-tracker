import { useState } from 'react';
import { Plus, Filter, AlertCircle, TrendingUp, DollarSign, Target } from 'lucide-react';
import { Button, Card, CardHeader, CardTitle, CardContent, LoadingSpinner } from '../components/ui';
import { BudgetCard } from '../components/budgets/BudgetCard';
import { BudgetForm } from '../components/budgets/BudgetForm';
import { useBudgets, useBudgetSummary, useBudgetAlerts, useBudgetActions } from '../hooks/useBudgets';
import { budgetService } from '../services/budgetService';
import { BudgetPeriod } from '../types/budgets';
import type { Budget, BudgetFilters } from '../types/budgets';

export function Budgets() {
  const [filters, setFilters] = useState<BudgetFilters>({});
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | undefined>();
  const [showFilters, setShowFilters] = useState(false);

  // Data fetching
  const { data: budgetData, isLoading: isBudgetsLoading, error: budgetsError } = useBudgets(filters);
  const { data: summary, isLoading: isSummaryLoading } = useBudgetSummary();
  const { data: alerts = [], isLoading: isAlertsLoading } = useBudgetAlerts();

  // Mutations
  const { create, update, delete: deleteBudget, isCreating, isUpdating, isDeleting } = useBudgetActions();

  const budgets = budgetData?.budgets || [];
  const isLoading = isBudgetsLoading || isSummaryLoading || isAlertsLoading;

  const handleCreateBudget = () => {
    setEditingBudget(undefined);
    setIsFormOpen(true);
  };

  const handleEditBudget = (budget: Budget) => {
    setEditingBudget(budget);
    setIsFormOpen(true);
  };

  const handleFormSubmit = (data: any) => {
    if (editingBudget) {
      update({ budgetId: editingBudget.id, budget: data }, {
        onSuccess: () => {
          setIsFormOpen(false);
          setEditingBudget(undefined);
        },
      });
    } else {
      create(data, {
        onSuccess: () => {
          setIsFormOpen(false);
        },
      });
    }
  };

  const handleDeleteBudget = (budgetId: string) => {
    deleteBudget(budgetId);
  };

  const handleFilterChange = (newFilters: Partial<BudgetFilters>) => {
    setFilters((prev: BudgetFilters) => ({ ...prev, ...newFilters }));
  };

  const clearFilters = () => {
    setFilters({});
  };

  const hasActiveFilters = Object.values(filters).some(value => value !== undefined && value !== '');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Budget Management
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Track and manage your spending budgets
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                onClick={() => setShowFilters(!showFilters)}
                className="relative"
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
                {hasActiveFilters && (
                  <span className="absolute -top-1 -right-1 h-2 w-2 bg-primary-600 rounded-full" />
                )}
              </Button>
              
              <Button onClick={handleCreateBudget}>
                <Plus className="h-4 w-4 mr-2" />
                New Budget
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alerts Section */}
        {alerts.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Budget Alerts
            </h2>
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div
                  key={`${alert.budget_id}-${alert.alert_type}`}
                  className={`p-4 rounded-lg border ${
                    alert.alert_type === 'exceeded'
                      ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                      : alert.alert_type === 'warning'
                      ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                      : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <AlertCircle className={`h-5 w-5 mt-0.5 ${
                      alert.alert_type === 'exceeded'
                        ? 'text-red-500'
                        : alert.alert_type === 'warning'
                        ? 'text-yellow-500'
                        : 'text-blue-500'
                    }`} />
                    <div className="flex-1">
                      <p className={`font-medium ${
                        alert.alert_type === 'exceeded'
                          ? 'text-red-700 dark:text-red-300'
                          : alert.alert_type === 'warning'
                          ? 'text-yellow-700 dark:text-yellow-300'
                          : 'text-blue-700 dark:text-blue-300'
                      }`}>
                        {alert.budget_name}
                        {alert.category_name && ` (${alert.category_name})`}
                      </p>
                      <p className={`text-sm ${
                        alert.alert_type === 'exceeded'
                          ? 'text-red-600 dark:text-red-400'
                          : alert.alert_type === 'warning'
                          ? 'text-yellow-600 dark:text-yellow-400'
                          : 'text-blue-600 dark:text-blue-400'
                      }`}>
                        {alert.message}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Budgets</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {summary.total_budgets}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Target className="h-5 w-5 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Budgeted</p>
                    <p className="text-2xl font-bold text-green-600">
                      {budgetService.formatCurrency(summary.total_budgeted_cents)}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <DollarSign className="h-5 w-5 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Spent</p>
                    <p className="text-2xl font-bold text-red-600">
                      {budgetService.formatCurrency(summary.total_spent_cents)}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-red-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-red-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Over Budget</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {summary.over_budget_count}
                    </p>
                  </div>
                  <div className="h-10 w-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <AlertCircle className="h-5 w-5 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        {showFilters && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-base">Filter Budgets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Period
                  </label>
                  <select
                    value={filters.period || ''}
                    onChange={(e) => handleFilterChange({ period: e.target.value as BudgetPeriod || undefined })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">All Periods</option>
                    {Object.values(BudgetPeriod).map((period) => (
                      <option key={period} value={period}>
                        {budgetService.getPeriodDisplayName(period as BudgetPeriod)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Status
                  </label>
                  <select
                    value={filters.is_active === undefined ? '' : filters.is_active.toString()}
                    onChange={(e) => handleFilterChange({ 
                      is_active: e.target.value === '' ? undefined : e.target.value === 'true' 
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">All Status</option>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Budget Status
                  </label>
                  <select
                    value={filters.over_budget === undefined ? '' : filters.over_budget.toString()}
                    onChange={(e) => handleFilterChange({ 
                      over_budget: e.target.value === '' ? undefined : e.target.value === 'true' 
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">All Budgets</option>
                    <option value="false">On Track</option>
                    <option value="true">Over Budget</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <Button variant="ghost" onClick={clearFilters} disabled={!hasActiveFilters}>
                    Clear Filters
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {/* Error State */}
        {budgetsError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-8">
            <p className="text-red-600 dark:text-red-400">
              Failed to load budgets. Please try refreshing the page.
            </p>
          </div>
        )}

        {/* Budget List */}
        {!isLoading && budgets.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {budgets.map((budget) => (
              <BudgetCard
                key={budget.id}
                budget={budget}
                onEdit={handleEditBudget}
                onDelete={handleDeleteBudget}
                isLoading={isDeleting}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && budgets.length === 0 && (
          <Card>
            <CardContent className="text-center py-12">
              <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                {hasActiveFilters ? 'No budgets match your filters' : 'No budgets yet'}
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {hasActiveFilters 
                  ? 'Try adjusting your filters to see more results.'
                  : 'Create your first budget to start tracking your spending.'
                }
              </p>
              {hasActiveFilters ? (
                <Button variant="ghost" onClick={clearFilters}>
                  Clear Filters
                </Button>
              ) : (
                <Button onClick={handleCreateBudget}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Budget
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Budget Form Modal */}
      <BudgetForm
        budget={editingBudget}
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false);
          setEditingBudget(undefined);
        }}
        onSubmit={handleFormSubmit}
        isLoading={isCreating || isUpdating}
      />
    </div>
  );
}