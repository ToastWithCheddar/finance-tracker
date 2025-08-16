import React, { useState } from 'react';
import { Edit, Trash2, Calendar, DollarSign, ToggleLeft, ToggleRight, CheckSquare, Square } from 'lucide-react';
import type { RecurringTransactionRule, RecurringRuleFilter } from '../../types/recurring';
import { useUpdateRecurringRule, useDeleteRecurringRule } from '../../hooks/useRecurring';
import { Button } from '../ui/Button';
import { formatCurrency } from '../../utils/currency';
import { RecurringRuleEditForm } from './RecurringRuleEditForm';
import { BulkActionsBar } from './BulkActionsBar';

interface RecurringRulesListProps {
  rules: RecurringTransactionRule[];
  pagination: {
    page: number;
    perPage: number;
    total: number;
    totalPages: number;
  };
  onFiltersChange: (filters: RecurringRuleFilter) => void;
  onPageChange: (page: number) => void;
}

export const RecurringRulesList: React.FC<RecurringRulesListProps> = ({
  rules,
  pagination,
  onPageChange,
}) => {
  const updateRule = useUpdateRecurringRule();
  const deleteRule = useDeleteRecurringRule();
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [editingRule, setEditingRule] = useState<RecurringTransactionRule | null>(null);
  const [selectedRules, setSelectedRules] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);

  const handleToggleActive = (rule: RecurringTransactionRule) => {
    updateRule.mutate({
      id: rule.id,
      updates: { is_active: !rule.is_active },
    });
  };

  const handleDelete = (ruleId: string) => {
    if (confirmDelete === ruleId) {
      deleteRule.mutate(ruleId);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(ruleId);
    }
  };

  const handleSelectRule = (ruleId: string) => {
    const newSelected = new Set(selectedRules);
    if (newSelected.has(ruleId)) {
      newSelected.delete(ruleId);
    } else {
      newSelected.add(ruleId);
    }
    setSelectedRules(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedRules.size === rules.length) {
      setSelectedRules(new Set());
    } else {
      setSelectedRules(new Set(rules.map(rule => rule.id)));
    }
  };

  const handleBulkActivate = () => {
    selectedRules.forEach(ruleId => {
      const rule = rules.find(r => r.id === ruleId);
      if (rule && !rule.is_active) {
        updateRule.mutate({
          id: ruleId,
          updates: { is_active: true },
        });
      }
    });
    setSelectedRules(new Set());
  };

  const handleBulkDeactivate = () => {
    selectedRules.forEach(ruleId => {
      const rule = rules.find(r => r.id === ruleId);
      if (rule && rule.is_active) {
        updateRule.mutate({
          id: ruleId,
          updates: { is_active: false },
        });
      }
    });
    setSelectedRules(new Set());
  };

  const handleBulkDelete = () => {
    if (bulkDeleteConfirm) {
      selectedRules.forEach(ruleId => {
        deleteRule.mutate(ruleId);
      });
      setSelectedRules(new Set());
      setBulkDeleteConfirm(false);
    } else {
      setBulkDeleteConfirm(true);
    }
  };

  const handleClearSelection = () => {
    setSelectedRules(new Set());
    setBulkDeleteConfirm(false);
  };

  const getFrequencyDisplay = (frequency: string, interval: number) => {
    const freqMap: Record<string, string> = {
      weekly: 'Week',
      biweekly: '2 Weeks',
      monthly: 'Month',
      quarterly: '3 Months',
      annually: 'Year',
    };
    const baseFreq = freqMap[frequency] || frequency;
    return interval === 1 ? `Every ${baseFreq}` : `Every ${interval} ${baseFreq}s`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getDaysUntilNext = (daysUntilNext: number | null) => {
    if (daysUntilNext === null) return 'Unknown';
    if (daysUntilNext < 0) return `${Math.abs(daysUntilNext)} days overdue`;
    if (daysUntilNext === 0) return 'Due today';
    if (daysUntilNext === 1) return 'Due tomorrow';
    return `Due in ${daysUntilNext} days`;
  };

  return (
    <div className="space-y-4">
      {/* Bulk Actions Header */}
      {rules.length > 0 && (
        <div className="flex items-center justify-between p-3 bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg">
          <label className="flex items-center cursor-pointer">
            <button
              onClick={handleSelectAll}
              className="flex items-center text-[hsl(var(--text))] hover:text-[hsl(var(--brand))]"
            >
              {selectedRules.size === rules.length ? (
                <CheckSquare className="h-5 w-5 mr-2" />
              ) : (
                <Square className="h-5 w-5 mr-2" />
              )}
              <span className="text-sm">
                {selectedRules.size === 0 
                  ? 'Select all' 
                  : selectedRules.size === rules.length 
                  ? 'Deselect all'
                  : `${selectedRules.size} selected`
                }
              </span>
            </button>
          </label>

          {selectedRules.size > 0 && (
            <div className="text-sm text-[hsl(var(--text))] opacity-70">
              Click actions below or use the bulk actions bar
            </div>
          )}
        </div>
      )}

      {/* Rules List */}
      <div className="space-y-3">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className={`border rounded-lg p-4 transition-all hover:shadow-md bg-[hsl(var(--surface))] border-[hsl(var(--border))] ${
              selectedRules.has(rule.id) ? 'ring-2 ring-[hsl(var(--brand))] border-[hsl(var(--brand))]' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              {/* Checkbox */}
              <div className="mr-3 pt-1">
                <button
                  onClick={() => handleSelectRule(rule.id)}
                  className="text-[hsl(var(--text))] hover:text-[hsl(var(--brand))]"
                >
                  {selectedRules.has(rule.id) ? (
                    <CheckSquare className="h-5 w-5" />
                  ) : (
                    <Square className="h-5 w-5" />
                  )}
                </button>
              </div>

              <div className="flex-1">
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <h3 className={`font-semibold ${
                      rule.is_active ? 'text-[hsl(var(--text))]' : 'text-[hsl(var(--text))] opacity-60'
                    }`}>
                      {rule.name}
                    </h3>
                    {!rule.is_confirmed && (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100">
                        Suggested
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleToggleActive(rule)}
                      disabled={updateRule.isPending}
                      className="focus:outline-none"
                    >
                      {rule.is_active ? (
                        <ToggleRight className="h-6 w-6 text-green-600" />
                      ) : (
                        <ToggleLeft className="h-6 w-6 text-gray-400" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Description */}
                <p className="mb-3 text-[hsl(var(--text))] opacity-80">{rule.description}</p>

                {/* Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                  {/* Amount */}
                  <div className="flex items-center space-x-2">
                    <DollarSign className="h-4 w-4 text-green-600 dark:text-green-300" />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">
                        {formatCurrency(rule.amount_dollars)}
                      </div>
                      <div className="text-xs text-[hsl(var(--text))] opacity-70">
                        ±{formatCurrency(rule.tolerance_cents / 100)} tolerance
                      </div>
                    </div>
                  </div>

                  {/* Frequency */}
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4 text-blue-600 dark:text-blue-300" />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">
                        {getFrequencyDisplay(rule.frequency, rule.interval)}
                      </div>
                      <div className="text-xs text-[hsl(var(--text))] opacity-70">
                        Next: {formatDate(rule.next_due_date)}
                      </div>
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex items-center space-x-2">
                    <div className={`h-2 w-2 rounded-full ${
                      rule.days_until_next !== null && rule.days_until_next < 0
                        ? 'bg-red-500'
                        : rule.days_until_next !== null && rule.days_until_next <= 7
                        ? 'bg-orange-500'
                        : 'bg-green-500'
                    }`} />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">
                        {getDaysUntilNext(rule.days_until_next)}
                      </div>
                      <div className="text-xs text-[hsl(var(--text))] opacity-70">
                        {rule.is_active ? 'Active' : 'Inactive'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Settings */}
                <div className="flex items-center space-x-4 text-sm text-[hsl(var(--text))] opacity-70">
                  {rule.auto_categorize && (
                    <span>✓ Auto-categorize</span>
                  )}
                  {rule.generate_notifications && (
                    <span>✓ Notifications</span>
                  )}
                  {rule.confidence_score && (
                    <span>{Math.round(rule.confidence_score * 100)}% confidence</span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-col space-y-2 ml-4">
                <Button
                  onClick={() => setEditingRule(rule)}
                  variant="outline"
                  size="sm"
                  className="text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
                >
                  <Edit className="h-4 w-4 mr-1" />
                  Edit
                </Button>
                
                <Button
                  onClick={() => handleDelete(rule.id)}
                  disabled={deleteRule.isPending}
                  variant="outline"
                  size="sm"
                  className={`${
                    confirmDelete === rule.id
                      ? 'border-red-300 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200'
                      : 'text-red-600 hover:text-red-800 dark:text-red-300 dark:hover:text-red-200'
                  }`}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  {confirmDelete === rule.id ? 'Confirm' : 'Delete'}
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-gray-500">
            Showing {(pagination.page - 1) * pagination.perPage + 1} to{' '}
            {Math.min(pagination.page * pagination.perPage, pagination.total)} of{' '}
            {pagination.total} results
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
              variant="outline"
              size="sm"
            >
              Previous
            </Button>
            
            <span className="px-3 py-1 text-sm text-gray-700">
              Page {pagination.page} of {pagination.totalPages}
            </span>
            
            <Button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page === pagination.totalPages}
              variant="outline"
              size="sm"
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Edit Rule Modal */}
      <RecurringRuleEditForm
        isOpen={!!editingRule}
        onClose={() => setEditingRule(null)}
        rule={editingRule}
      />

      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selectedRules.size}
        onActivateSelected={handleBulkActivate}
        onDeactivateSelected={handleBulkDeactivate}
        onDeleteSelected={handleBulkDelete}
        onClearSelection={handleClearSelection}
        isLoading={updateRule.isPending || deleteRule.isPending}
      />
    </div>
  );
};