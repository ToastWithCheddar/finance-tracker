import React, { useState } from 'react';
import { 
  Settings, 
  Edit, 
  Trash2, 
  Copy, 
  Play, 
  Pause, 
  ChevronDown,
  ChevronUp,
  Filter,
  Search,
  MoreVertical,
  Target,
  Zap
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { formatDistanceToNow } from 'date-fns';
import { useCategorizationRuleActions } from '../../hooks/useCategorizationRules';
import type { 
  CategorizationRule, 
  CategorizationRuleFilter 
} from '../../types/categorizationRules';

/**
 * ARCHITECTURAL NOTE: This component should be moved to frontend/src/features/automation/
 * 
 * This component is part of the automation rules feature set and should be co-located
 * with AutomationRulesTab, RuleTemplateGallery, and other automation components.
 * See AutomationRulesTab.tsx for complete architectural documentation and migration plan.
 */

interface CategorizationRulesListProps {
  rules: CategorizationRule[];
  pagination: {
    page: number;
    perPage: number;
    total: number;
    totalPages: number;
  };
  onFiltersChange: (filters: CategorizationRuleFilter) => void;
  onPageChange: (page: number) => void;
  onSelectRule: (rule: CategorizationRule) => void;
}

interface RuleCardProps {
  rule: CategorizationRule;
  onEdit: (rule: CategorizationRule) => void;
  onDelete: (rule: CategorizationRule) => void;
  onDuplicate: (ruleId: string) => void;
  onToggleActive: (ruleId: string, isActive: boolean) => void;
  onSelect: (rule: CategorizationRule) => void;
  isLoading: boolean;
}

const RuleCard: React.FC<RuleCardProps> = ({
  rule,
  onEdit,
  onDelete,
  onDuplicate,
  onToggleActive,
  onSelect,
  isLoading
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const getPriorityColor = (priority: number) => {
    if (priority <= 25) return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-100';
    if (priority <= 50) return 'text-orange-600 bg-orange-100 dark:bg-orange-900 dark:text-orange-100';
    if (priority <= 75) return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-100';
    return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-100';
  };

  const getSuccessRateColor = (rate?: number) => {
    if (!rate) return 'text-gray-600';
    if (rate < 0.5) return 'text-red-600';
    if (rate < 0.8) return 'text-orange-600';
    return 'text-green-600';
  };

  return (
    <div className={`
      bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg p-4 
      transition-all duration-200 hover:shadow-md cursor-pointer
      ${!rule.is_active ? 'opacity-60' : ''}
    `}>
      {/* Header */}
      <div className="flex items-center justify-between" onClick={() => onSelect(rule)}>
        <div className="flex items-center space-x-3 flex-1">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              rule.is_active 
                ? 'bg-blue-100 dark:bg-blue-900' 
                : 'bg-gray-100 dark:bg-gray-900'
            }`}>
              {rule.is_active ? (
                <Zap className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              ) : (
                <Pause className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              )}
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-[hsl(var(--text))] truncate">
              {rule.name}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(rule.priority)}`}>
                Priority {rule.priority}
              </span>
              <span className={`px-2 py-1 text-xs font-medium rounded ${
                rule.is_active 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100'
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100'
              }`}>
                {rule.is_active ? 'Active' : 'Inactive'}
              </span>
              {rule.times_applied > 0 && (
                <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                  {rule.times_applied} uses
                </span>
              )}
            </div>
            {rule.description && (
              <p className="text-sm text-[hsl(var(--text))] opacity-70 mt-1 truncate">
                {rule.description}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div className="text-right">
            {rule.success_rate !== undefined && (
              <p className={`text-sm font-medium ${getSuccessRateColor(rule.success_rate)}`}>
                {Math.round(rule.success_rate * 100)}% success
              </p>
            )}
            {rule.last_applied_at && (
              <p className="text-xs text-[hsl(var(--text))] opacity-70">
                Last used {formatDistanceToNow(new Date(rule.last_applied_at), { addSuffix: true })}
              </p>
            )}
          </div>
          
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setShowActions(!showActions);
              }}
              disabled={isLoading}
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
            
            {showActions && (
              <div className="absolute right-0 mt-2 w-48 bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg shadow-lg z-10">
                <div className="p-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(rule);
                      setShowActions(false);
                    }}
                    disabled={isLoading}
                    className="flex items-center w-full px-3 py-2 text-sm text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] rounded disabled:opacity-50"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit rule
                  </button>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleActive(rule.id, !rule.is_active);
                      setShowActions(false);
                    }}
                    disabled={isLoading}
                    className="flex items-center w-full px-3 py-2 text-sm text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] rounded disabled:opacity-50"
                  >
                    {rule.is_active ? (
                      <>
                        <Pause className="h-4 w-4 mr-2" />
                        Deactivate
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Activate
                      </>
                    )}
                  </button>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDuplicate(rule.id);
                      setShowActions(false);
                    }}
                    disabled={isLoading}
                    className="flex items-center w-full px-3 py-2 text-sm text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] rounded disabled:opacity-50"
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    Duplicate
                  </button>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(rule);
                      setShowActions(false);
                    }}
                    disabled={isLoading}
                    className="flex items-center w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </button>
                </div>
              </div>
            )}
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setShowDetails(!showDetails);
            }}
          >
            {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Details */}
      {showDetails && (
        <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-[hsl(var(--text))] mb-2">Conditions</h4>
              <div className="space-y-1 text-sm">
                {Object.entries(rule.conditions).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-[hsl(var(--text))] opacity-70 capitalize">
                      {key.replace('_', ' ')}:
                    </span>
                    <span className="text-[hsl(var(--text))] text-right max-w-40 truncate">
                      {Array.isArray(value) ? value.join(', ') : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-[hsl(var(--text))] mb-2">Actions</h4>
              <div className="space-y-1 text-sm">
                {Object.entries(rule.actions).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-[hsl(var(--text))] opacity-70 capitalize">
                      {key.replace('_', ' ')}:
                    </span>
                    <span className="text-[hsl(var(--text))] text-right max-w-40 truncate">
                      {Array.isArray(value) ? value.join(', ') : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-[hsl(var(--text))]">{rule.times_applied}</p>
                <p className="text-xs text-[hsl(var(--text))] opacity-70">Times Applied</p>
              </div>
              <div>
                <p className={`text-2xl font-bold ${getSuccessRateColor(rule.success_rate)}`}>
                  {rule.success_rate ? Math.round(rule.success_rate * 100) : 0}%
                </p>
                <p className="text-xs text-[hsl(var(--text))] opacity-70">Success Rate</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-[hsl(var(--text))]">{rule.priority}</p>
                <p className="text-xs text-[hsl(var(--text))] opacity-70">Priority</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const CategorizationRulesList: React.FC<CategorizationRulesListProps> = ({
  rules,
  pagination,
  onFiltersChange,
  onPageChange,
  onSelectRule
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; rule?: CategorizationRule }>({
    isOpen: false
  });
  
  const actions = useCategorizationRuleActions();

  // Filter rules based on search
  const filteredRules = rules.filter(rule => {
    const matchesSearch = !searchTerm || 
      rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (rule.description && rule.description.toLowerCase().includes(searchTerm.toLowerCase()));
    
    return matchesSearch;
  });

  /**
   * Opens edit modal for a categorization rule
   * @param rule - The complete rule object to edit
   * 
   * TODO: Implement CategorizationRuleEditForm modal component
   * Implementation should:
   * 1. Open a modal with a form component (e.g., CategorizationRuleEditForm)
   * 2. Pre-populate form fields with current rule data:
   *    - name, description, priority, is_active status
   *    - conditions array (merchant patterns, amount ranges, etc.)
   *    - actions array (target category, confidence thresholds)
   * 3. Provide validation for:
   *    - Required fields (name, at least one condition, one action)
   *    - Condition format and logical consistency
   *    - Priority uniqueness and valid range
   * 4. Handle form submission with optimistic updates
   * 5. Show success/error feedback and refresh rules list
   */
  const handleEdit = (rule: CategorizationRule) => {
    // For now, logging the complete rule data for future implementation
    console.log('Edit rule requested:', {
      id: rule.id,
      name: rule.name,
      description: rule.description,
      priority: rule.priority,
      conditions: rule.conditions,
      actions: rule.actions,
      is_active: rule.is_active
    });
  };

  const handleDelete = (rule: CategorizationRule) => {
    setDeleteConfirm({ isOpen: true, rule });
  };

  const handleDeleteConfirm = () => {
    if (deleteConfirm.rule) {
      actions.delete.mutate(deleteConfirm.rule.id);
    }
    setDeleteConfirm({ isOpen: false });
  };

  const handleDuplicate = (ruleId: string) => {
    actions.duplicate.mutate({ ruleId });
  };

  const handleToggleActive = (ruleId: string, isActive: boolean) => {
    actions.update.mutate({
      ruleId,
      updates: { is_active: isActive }
    });
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[hsl(var(--text))] opacity-50" />
          <input
            type="text"
            placeholder="Search rules..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--surface))] text-[hsl(var(--text))] placeholder-[hsl(var(--text))/0.5] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-transparent"
          />
        </div>
        
        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center"
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
        </Button>
      </div>

      {/* Rule Cards */}
      <div className="space-y-4">
        {filteredRules.map((rule) => (
          <RuleCard
            key={rule.id}
            rule={rule}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onDuplicate={handleDuplicate}
            onToggleActive={handleToggleActive}
            onSelect={onSelectRule}
            isLoading={actions.isLoading}
          />
        ))}
      </div>

      {filteredRules.length === 0 && searchTerm && (
        <div className="text-center py-8">
          <Search className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
          <p className="text-[hsl(var(--text))] opacity-80">No rules match your search.</p>
          <p className="text-sm text-[hsl(var(--text))] opacity-70">
            Try adjusting your search terms or clearing the search.
          </p>
        </div>
      )}

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-[hsl(var(--text))/0.75]">
            Showing {(pagination.page - 1) * pagination.perPage + 1} to{' '}
            {Math.min(pagination.page * pagination.perPage, pagination.total)} of{' '}
            {pagination.total} rules
          </div>
          
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => onPageChange(Math.max(1, pagination.page - 1))}
              disabled={pagination.page === 1}
            >
              Previous
            </Button>
            
            {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
              const page = pagination.page <= 3 
                ? i + 1 
                : Math.max(1, Math.min(pagination.totalPages - 4, pagination.page - 2)) + i;
              
              return (
                <Button
                  key={page}
                  variant={pagination.page === page ? "primary" : "outline"}
                  onClick={() => onPageChange(page)}
                >
                  {page}
                </Button>
              );
            })}
            
            <Button
              variant="outline"
              onClick={() => onPageChange(Math.min(pagination.totalPages, pagination.page + 1))}
              disabled={pagination.page === pagination.totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false })}
        title="Delete Categorization Rule"
      >
        <div className="space-y-4">
          <p>
            Are you sure you want to delete the rule "<strong>{deleteConfirm.rule?.name}</strong>"?
          </p>
          <p className="text-sm text-[hsl(var(--text))/0.75]">
            This action cannot be undone. The rule will no longer automatically categorize transactions.
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
              Delete Rule
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};