import React, { useState } from 'react';
import { 
  TestTube, 
  Play, 
  Code, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Lightbulb,
  Target
} from 'lucide-react';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useTestRuleConditions } from '../../hooks/useCategorizationRules';
import type { 
  CategorizationRuleConditions,
  RuleTestResult 
} from '../../types/categorizationRules';

export const RuleTestingPlayground: React.FC = () => {
  const [conditions, setConditions] = useState<CategorizationRuleConditions>({
    merchant_contains: ['starbucks'],
    amount_range: { min_cents: 100, max_cents: 2000 }
  });
  const [conditionsJson, setConditionsJson] = useState(JSON.stringify(conditions, null, 2));
  const [limit, setLimit] = useState(50);
  const [isJsonValid, setIsJsonValid] = useState(true);
  const [enableTesting, setEnableTesting] = useState(false);

  const {
    data: testResults,
    isLoading: isTestingRules,
    error: testError
  } = useTestRuleConditions(conditions, limit, enableTesting);

  const handleConditionsChange = (value: string) => {
    setConditionsJson(value);
    
    try {
      const parsed = JSON.parse(value);
      setConditions(parsed);
      setIsJsonValid(true);
    } catch (error) {
      setIsJsonValid(false);
    }
  };

  const handleRunTest = () => {
    if (isJsonValid) {
      setEnableTesting(true);
      // The query will automatically run when enableTesting becomes true
      setTimeout(() => setEnableTesting(false), 100); // Reset to prevent automatic re-runs
    }
  };

  const handleLoadExample = (example: CategorizationRuleConditions) => {
    const exampleJson = JSON.stringify(example, null, 2);
    setConditionsJson(exampleJson);
    setConditions(example);
    setIsJsonValid(true);
  };

  const examples = [
    {
      name: 'Coffee Shops',
      conditions: {
        merchant_contains: ['starbucks', 'coffee', 'cafe'],
        amount_range: { min_cents: 100, max_cents: 2000 }
      }
    },
    {
      name: 'Gas Stations',
      conditions: {
        merchant_contains: ['shell', 'exxon', 'chevron', 'bp'],
        amount_range: { min_cents: 2000, max_cents: 10000 }
      }
    },
    {
      name: 'Online Shopping',
      conditions: {
        merchant_contains: ['amazon', 'ebay', 'etsy'],
        description_contains: ['amzn', 'marketplace']
      }
    },
    {
      name: 'Subscriptions',
      conditions: {
        merchant_contains: ['netflix', 'spotify', 'apple'],
        amount_range: { min_cents: 500, max_cents: 2000 }
      }
    }
  ];

  return (
    <div className="space-y-6">
      {/* Testing Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
              <Code className="h-5 w-5 mr-2" />
              Rule Conditions
            </h3>
            
            {/* Example Templates */}
            <div className="mb-4">
              <p className="text-sm text-[hsl(var(--text))] opacity-70 mb-2">
                Quick Examples:
              </p>
              <div className="flex flex-wrap gap-2">
                {examples.map((example) => (
                  <Button
                    key={example.name}
                    size="sm"
                    variant="outline"
                    onClick={() => handleLoadExample(example.conditions)}
                  >
                    <Lightbulb className="h-3 w-3 mr-1" />
                    {example.name}
                  </Button>
                ))}
              </div>
            </div>

            {/* JSON Editor */}
            <div className="relative">
              <textarea
                value={conditionsJson}
                onChange={(e) => handleConditionsChange(e.target.value)}
                placeholder="Enter rule conditions as JSON..."
                className={`w-full h-64 p-4 border rounded-lg font-mono text-sm bg-[hsl(var(--surface))] text-[hsl(var(--text))] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-transparent ${
                  isJsonValid 
                    ? 'border-[hsl(var(--border))]' 
                    : 'border-red-500 focus:ring-red-500'
                }`}
              />
              {!isJsonValid && (
                <div className="absolute top-2 right-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                </div>
              )}
            </div>
            
            {!isJsonValid && (
              <p className="text-sm text-red-600">Invalid JSON format</p>
            )}
          </div>

          {/* Test Controls */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label htmlFor="limit" className="text-sm text-[hsl(var(--text))]">
                Test limit:
              </label>
              <input
                id="limit"
                type="number"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                min="1"
                max="1000"
                className="w-20 px-2 py-1 border border-[hsl(var(--border))] rounded bg-[hsl(var(--surface))] text-[hsl(var(--text))] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-transparent"
              />
            </div>
            
            <Button
              onClick={handleRunTest}
              disabled={!isJsonValid || isTestingRules}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isTestingRules ? (
                <>
                  <LoadingSpinner className="h-4 w-4 mr-2" />
                  Testing...
                </>
              ) : (
                <>
                  <TestTube className="h-4 w-4 mr-2" />
                  Run Test
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Results Section */}
        <div>
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-4 flex items-center">
            <Target className="h-5 w-5 mr-2" />
            Test Results
          </h3>

          {isTestingRules && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          )}

          {testError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <XCircle className="h-5 w-5 text-red-500 mr-2" />
                <h4 className="font-medium text-red-800 dark:text-red-200">Test Failed</h4>
              </div>
              <p className="text-sm text-red-700 dark:text-red-300">
                {testError.message || 'Failed to test rule conditions'}
              </p>
            </div>
          )}

          {testResults && !isTestingRules && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-[hsl(var(--text))]">Test Summary</h4>
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <span className="text-sm font-medium text-green-600">
                      {testResults.length} matches found
                    </span>
                  </div>
                </div>
                <p className="text-sm text-[hsl(var(--text))] opacity-70">
                  Testing conditions against the last {limit} transactions
                </p>
              </div>

              {/* Results List */}
              <div className="max-h-80 overflow-y-auto space-y-2">
                {testResults.map((result, index) => (
                  <div
                    key={result.transaction_id}
                    className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg p-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h5 className="font-medium text-[hsl(var(--text))] text-sm">
                            {result.transaction_merchant || result.transaction_description}
                          </h5>
                          <span className="text-xs text-[hsl(var(--text))] opacity-70">
                            ${(result.transaction_amount_cents / 100).toFixed(2)}
                          </span>
                        </div>
                        <p className="text-xs text-[hsl(var(--text))] opacity-70">
                          {new Date(result.transaction_date).toLocaleDateString()}
                        </p>
                        {result.matching_conditions.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-[hsl(var(--text))] opacity-70 mb-1">
                              Matching conditions:
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {result.matching_conditions.map((condition, idx) => (
                                <span
                                  key={idx}
                                  className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100 rounded"
                                >
                                  {condition}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {result.would_match ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs font-medium text-[hsl(var(--text))]">
                          {Math.round(result.match_score * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {testResults.length === 0 && (
                <div className="text-center py-8">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-yellow-500" />
                  <p className="text-[hsl(var(--text))] opacity-80">No matching transactions found</p>
                  <p className="text-sm text-[hsl(var(--text))] opacity-70">
                    Try adjusting your conditions or increasing the test limit
                  </p>
                </div>
              )}
            </div>
          )}

          {!testResults && !isTestingRules && !testError && (
            <div className="text-center py-12">
              <TestTube className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
              <p className="text-[hsl(var(--text))] opacity-80">Ready to test</p>
              <p className="text-sm text-[hsl(var(--text))] opacity-70">
                Enter rule conditions and click "Run Test" to see matches
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Help Section */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2 flex items-center">
          <Lightbulb className="h-4 w-4 mr-2" />
          Rule Conditions Reference
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-700 dark:text-blue-300">
          <div>
            <p className="font-medium mb-1">Merchant Matching:</p>
            <ul className="text-xs space-y-1 ml-4">
              <li>• <code>merchant_contains</code>: ["starbucks", "coffee"]</li>
              <li>• <code>merchant_exact</code>: ["Starbucks Store"]</li>
              <li>• <code>merchant_regex</code>: "^(Starbucks|Coffee).*"</li>
            </ul>
          </div>
          <div>
            <p className="font-medium mb-1">Amount Filtering:</p>
            <ul className="text-xs space-y-1 ml-4">
              <li>• <code>amount_range</code>: {"{"}"min_cents": 100, "max_cents": 2000{"}"}</li>
              <li>• <code>amount_exact</code>: 1299</li>
            </ul>
          </div>
          <div>
            <p className="font-medium mb-1">Description Matching:</p>
            <ul className="text-xs space-y-1 ml-4">
              <li>• <code>description_contains</code>: ["purchase", "payment"]</li>
              <li>• <code>description_regex</code>: ".*RECURRING.*"</li>
            </ul>
          </div>
          <div>
            <p className="font-medium mb-1">Other Conditions:</p>
            <ul className="text-xs space-y-1 ml-4">
              <li>• <code>transaction_type</code>: "expense" | "income"</li>
              <li>• <code>account_type</code>: ["checking", "credit"]</li>
              <li>• <code>exclude_category_ids</code>: ["uuid1", "uuid2"]</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};