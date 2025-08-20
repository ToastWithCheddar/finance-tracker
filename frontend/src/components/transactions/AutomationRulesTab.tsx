import React, { useState } from 'react';
import { 
  Plus, 
  Settings, 
  AlertCircle, 
  Zap, 
  Target, 
  TrendingUp, 
  TestTube, 
  Download,
  Upload,
  Copy,
  Trash2,
  Play
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { 
  useCategorizationRules, 
  useRuleTemplates, 
  useRuleStatistics,
  useCategorizationRuleActions 
} from '../../hooks/useCategorizationRules';
import { CategorizationRulesList } from './CategorizationRulesList';
import { RuleTemplateGallery } from './RuleTemplateGallery';
import { RuleTestingPlayground } from './RuleTestingPlayground';
import { RuleEffectivenessMetrics } from './RuleEffectivenessMetrics';
import type {
  CategorizationRuleFilter,
  CategorizationRule,
  CategorizationRuleTemplate,
  RuleStatistics
} from '../../types/categorizationRules';

/**
 * ARCHITECTURAL NOTE: Component Extraction Required
 * 
 * This component and its related automation/rules components should be extracted 
 * from the transactions directory into a dedicated feature module.
 * 
 * Current location: frontend/src/components/transactions/
 * Proposed location: frontend/src/features/automation/
 * 
 * Rationale:
 * - The automation rules feature has grown complex enough to warrant its own module
 * - This reduces coupling between transaction CRUD and automation logic
 * - Improves code organization and maintainability
 * - Aligns with domain-driven design principles
 * 
 * Components to move:
 * - AutomationRulesTab.tsx (this file)
 * - CategorizationRulesList.tsx
 * - RuleTemplateGallery.tsx
 * - RuleTestingPlayground.tsx
 * - RuleEffectivenessMetrics.tsx
 * 
 * Dependencies to update:
 * - Move related hooks from useCategorizationRules to features/automation/hooks/
 * - Move types from types/categorizationRules.ts to features/automation/types/
 * - Update import paths in parent components
 * 
 * Benefits of extraction:
 * - Clear separation of concerns
 * - Easier to locate automation-related code
 * - Reduced bundle size for transaction-only pages
 * - Better testability and maintainability
 * - Potential for lazy loading of automation features
 */

// Type guard functions
const isRuleStatistics = (data: any): data is RuleStatistics => {
  return data && typeof data === 'object' && typeof data.total_rules === 'number';
};

const isRuleTemplates = (data: any): data is CategorizationRuleTemplate[] => {
  return Array.isArray(data);
};

export const AutomationRulesTab: React.FC = () => {
  // State for different sections
  const [activeSection, setActiveSection] = useState<'rules' | 'templates' | 'testing' | 'metrics'>('rules');
  const [showCreateRuleForm, setShowCreateRuleForm] = useState(false);
  const [ruleFilters, setRuleFilters] = useState<CategorizationRuleFilter>({});
  const [rulePage, setRulePage] = useState(1);
  const [selectedRule, setSelectedRule] = useState<CategorizationRule | null>(null);

  // Data fetching
  const {
    data: rulesData,
    isLoading: rulesLoading,
    error: rulesError
  } = useCategorizationRules(rulePage, 20, ruleFilters);

  const {
    data: templates,
    isLoading: templatesLoading,
    error: templatesError
  } = useRuleTemplates();

  const {
    data: statistics,
    isLoading: statisticsLoading,
    error: statisticsError
  } = useRuleStatistics();

  // Actions
  const ruleActions = useCategorizationRuleActions();

  // Handlers
  const handleRuleFiltersChange = (newFilters: CategorizationRuleFilter) => {
    setRuleFilters(newFilters);
    setRulePage(1);
  };

  const handleRulePageChange = (newPage: number) => {
    setRulePage(newPage);
  };

  const handleClearRuleFilters = () => {
    setRuleFilters({});
    setRulePage(1);
  };

  const handleExportRules = () => {
    ruleActions.export.mutate('json');
  };

  const handleImportRules = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      ruleActions.import.mutate(file);
    }
  };

  // Section configuration
  const sections = [
    {
      id: 'rules' as const,
      label: 'Rules',
      icon: Settings,
      description: 'Manage categorization rules'
    },
    {
      id: 'templates' as const,
      label: 'Templates',
      icon: Copy,
      description: 'Browse rule templates'
    },
    {
      id: 'testing' as const,
      label: 'Testing',
      icon: TestTube,
      description: 'Test rule conditions'
    },
    {
      id: 'metrics' as const,
      label: 'Metrics',
      icon: TrendingUp,
      description: 'View rule effectiveness'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[hsl(var(--text))]">Automation Rules</h2>
          <p className="text-[hsl(var(--text))] opacity-70 mt-1">
            Configure intelligent categorization rules and templates
          </p>
        </div>
        <div className="flex space-x-3">
          <input
            type="file"
            accept=".json"
            onChange={handleImportRules}
            className="hidden"
            id="import-rules"
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('import-rules')?.click()}
            disabled={ruleActions.isLoading}
          >
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button
            variant="outline"
            onClick={handleExportRules}
            disabled={ruleActions.isLoading}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button
            onClick={() => setShowCreateRuleForm(true)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Rule
          </Button>
        </div>
      </div>

      {/* Statistics Overview */}
      {statisticsLoading ? (
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
      ) : statisticsError ? (
        <Card>
          <div className="p-4 text-center">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-500" />
            <p className="text-red-600 dark:text-red-400">Failed to load statistics</p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70 mt-1">
              {statisticsError.message || 'Please try refreshing the page'}
            </p>
          </div>
        </Card>
      ) : isRuleStatistics(statistics) ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <div className="p-4">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Settings className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="ml-4">
                  <p className="text-2xl font-bold text-[hsl(var(--text))]">{statistics.total_rules}</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">Total Rules</p>
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="p-4">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <Zap className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div className="ml-4">
                  <p className="text-2xl font-bold text-[hsl(var(--text))]">{statistics.active_rules}</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">Active Rules</p>
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="p-4">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                  <Target className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="ml-4">
                  <p className="text-2xl font-bold text-[hsl(var(--text))]">{statistics.total_applications}</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">Applications</p>
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="p-4">
              <div className="flex items-center">
                <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                </div>
                <div className="ml-4">
                  <p className="text-2xl font-bold text-[hsl(var(--text))]">
                    {Math.round(statistics.average_success_rate * 100)}%
                  </p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">Success Rate</p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      ) : null}

      {/* Section Navigation */}
      <div className="flex space-x-1 p-1 bg-[hsl(var(--border)/0.15)] rounded-lg w-fit">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`
                flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all
                ${activeSection === section.id
                  ? 'bg-[hsl(var(--surface))] text-[hsl(var(--text))] shadow-sm'
                  : 'text-[hsl(var(--text))/0.7] hover:text-[hsl(var(--text))]'
                }
              `}
              title={section.description}
            >
              <Icon className="h-4 w-4 mr-2" />
              {section.label}
            </button>
          );
        })}
      </div>

      {/* Section Content */}
      <div className="space-y-6">
        {/* Rules Section */}
        {activeSection === 'rules' && (
          <Card>
            <CardHeader className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))]">
              <div className="flex items-center">
                <Settings className="h-5 w-5 text-blue-500 mr-2" />
                <CardTitle>Categorization Rules</CardTitle>
              </div>
              <div className="flex items-center gap-4">
                {rulesData && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Total</span>
                    <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                      {rulesData.total}
                    </span>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {rulesLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : rulesError ? (
                <div className="text-center py-8">
                  <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
                  <p className="text-red-600 dark:text-red-400 mb-2">Failed to load categorization rules</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">
                    {rulesError.message || 'Please try refreshing the page'}
                  </p>
                </div>
              ) : rulesData && rulesData.items.length > 0 ? (
                <CategorizationRulesList
                  rules={rulesData.items}
                  pagination={{
                    page: rulesData.page,
                    perPage: rulesData.per_page,
                    total: rulesData.total,
                    totalPages: rulesData.total_pages,
                  }}
                  onFiltersChange={handleRuleFiltersChange}
                  onPageChange={handleRulePageChange}
                  onSelectRule={setSelectedRule}
                />
              ) : (
                <div className="text-center py-8">
                  <Settings className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
                  <p className="text-[hsl(var(--text))] opacity-80">
                    {Object.values(ruleFilters).some(v => v !== undefined && v !== '') 
                      ? 'No rules match your current filters.' 
                      : 'No categorization rules found.'
                    }
                  </p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">
                    {Object.values(ruleFilters).some(v => v !== undefined && v !== '') 
                      ? 'Try adjusting your filters or clearing them to see all rules.'
                      : 'Create your first rule or browse templates to get started.'
                    }
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Templates Section */}
        {activeSection === 'templates' && (
          <Card>
            <CardHeader className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))]">
              <div className="flex items-center">
                <Copy className="h-5 w-5 text-blue-500 mr-2" />
                <CardTitle>Rule Templates</CardTitle>
              </div>
              <div className="flex items-center gap-4">
                {isRuleTemplates(templates) && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wide text-[hsl(var(--text))] opacity-60">Available</span>
                    <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                      {templates.length}
                    </span>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {templatesLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : templatesError ? (
                <div className="text-center py-8">
                  <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
                  <p className="text-red-600 dark:text-red-400 mb-2">Failed to load rule templates</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">
                    {templatesError.message || 'Please try refreshing the page'}
                  </p>
                </div>
              ) : isRuleTemplates(templates) && templates.length > 0 ? (
                <RuleTemplateGallery templates={templates} />
              ) : (
                <div className="text-center py-8">
                  <Copy className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
                  <p className="text-[hsl(var(--text))] opacity-80">No rule templates available.</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">
                    Check back later or create your own custom rules.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Testing Section */}
        {activeSection === 'testing' && (
          <Card>
            <CardHeader className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))]">
              <div className="flex items-center">
                <TestTube className="h-5 w-5 text-blue-500 mr-2" />
                <CardTitle>Rule Testing Playground</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <RuleTestingPlayground />
            </CardContent>
          </Card>
        )}

        {/* Metrics Section */}
        {activeSection === 'metrics' && (
          <Card>
            <CardHeader className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))]">
              <div className="flex items-center">
                <TrendingUp className="h-5 w-5 text-blue-500 mr-2" />
                <CardTitle>Rule Effectiveness Metrics</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <RuleEffectivenessMetrics selectedRule={selectedRule} />
            </CardContent>
          </Card>
        )}
      </div>

      {/* Quick Actions for Rules */}
      {rulesData && rulesData.items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Play className="h-5 w-5 text-green-500 mr-2" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button
                variant="outline"
                className="flex items-center justify-center p-4 h-auto"
                onClick={() => {
                  /**
                   * TODO: Implement bulk rule application to recent transactions
                   * Implementation should:
                   * 1. Show confirmation modal with:
                   *    - Number of active rules to apply
                   *    - Date range for "recent" transactions (e.g., last 30 days)
                   *    - Expected number of transactions to be processed
                   *    - Warning about overriding existing categorizations
                   * 2. Create background job to:
                   *    - Fetch uncategorized transactions from date range
                   *    - Apply rules in priority order (first match wins)
                   *    - Track success/failure counts per rule
                   *    - Handle conflicts and rule overlaps
                   * 3. Show progress indicator during processing
                   * 4. Display results summary:
                   *    - Transactions categorized per rule
                   *    - Any conflicts or failures
                   *    - Option to review changes before finalizing
                   * 5. Refresh transaction list and rule effectiveness metrics
                   */
                  console.log('Apply all rules to recent transactions');
                }}
                disabled={ruleActions.isLoading}
              >
                <div className="text-center">
                  <Zap className="h-6 w-6 mx-auto mb-2 text-blue-500" />
                  <p className="font-medium">Apply All Rules</p>
                  <p className="text-sm opacity-70">To recent transactions</p>
                </div>
              </Button>

              <Button
                variant="outline"
                className="flex items-center justify-center p-4 h-auto"
                onClick={() => {
                  /**
                   * TODO: Implement rule testing functionality
                   * Implementation should:
                   * 1. Open rule testing modal with:
                   *    - Historical date range selector (e.g., last 3 months)
                   *    - Option to test against specific transaction subset
                   *    - Choice between dry-run vs actual categorization
                   * 2. Run simulation engine that:
                   *    - Fetches historical transactions from selected period
                   *    - Applies each rule and tracks matches/misses
                   *    - Identifies rule conflicts and overlaps
                   *    - Calculates accuracy metrics per rule
                   *    - Detects rules that never match (potential dead rules)
                   * 3. Display comprehensive test results:
                   *    - Rule-by-rule performance metrics
                   *    - Transaction coverage analysis
                   *    - Suggested rule improvements or reordering
                   *    - Visual charts showing rule effectiveness
                   * 4. Allow drill-down into specific rule matches for debugging
                   * 5. Option to export test results for further analysis
                   */
                  console.log('Test all rules');
                }}
                disabled={ruleActions.isLoading}
              >
                <div className="text-center">
                  <TestTube className="h-6 w-6 mx-auto mb-2 text-purple-500" />
                  <p className="font-medium">Test All Rules</p>
                  <p className="text-sm opacity-70">Against history</p>
                </div>
              </Button>

              <Button
                variant="outline"
                className="flex items-center justify-center p-4 h-auto"
                onClick={() => {
                  /**
                   * TODO: Implement rule order optimization algorithm
                   * Implementation should:
                   * 1. Show optimization preview modal with:
                   *    - Current rule order vs proposed optimized order
                   *    - Explanation of optimization criteria (frequency, accuracy, conflicts)
                   *    - Expected performance improvements
                   *    - Warning about potential behavior changes
                   * 2. Run optimization algorithm that:
                   *    - Analyzes historical rule match frequency and accuracy
                   *    - Identifies most frequently matching rules for prioritization
                   *    - Detects rule conflicts and suggests resolution order
                   *    - Considers rule specificity (specific rules before general ones)
                   *    - Accounts for user-defined priority overrides
                   * 3. Generate optimized rule ordering based on:
                   *    - Match frequency (high-frequency rules first)
                   *    - Accuracy scores (reliable rules prioritized)
                   *    - Conflict resolution (specific beats general)
                   *    - Processing efficiency (simple conditions first)
                   * 4. Allow user to review and approve changes before applying
                   * 5. Update rule order and refresh effectiveness metrics
                   */
                  console.log('Optimize rule order');
                }}
                disabled={ruleActions.isLoading}
              >
                <div className="text-center">
                  <Target className="h-6 w-6 mx-auto mb-2 text-green-500" />
                  <p className="font-medium">Optimize Order</p>
                  <p className="text-sm opacity-70">By effectiveness</p>
                </div>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};