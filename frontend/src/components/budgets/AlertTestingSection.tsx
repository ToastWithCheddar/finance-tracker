import { useState } from 'react';
import { TestTube, Eye, Info, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useBudgetAlertActions } from '../../hooks/useBudgetAlerts';
import type { Budget } from '../../types/budgets';

interface AlertTestingSectionProps {
  budget: Budget;
}

export function AlertTestingSection({ budget }: AlertTestingSectionProps) {
  const alertActions = useBudgetAlertActions();
  const [testAmountInput, setTestAmountInput] = useState('');

  const handleTestAlert = () => {
    const testAmount = parseFloat(testAmountInput);
    if (isNaN(testAmount) || testAmount <= 0) {
      toast.error('Please enter a valid test amount');
      return;
    }

    alertActions.sendTest({
      budget_id: budget.id,
      test_threshold: 0.8,
      test_amount_cents: Math.round(testAmount * 100)
    });
  };

  const handlePreviewAlert = () => {
    const testAmount = parseFloat(testAmountInput);
    if (isNaN(testAmount) || testAmount <= 0) {
      toast.error('Please enter a valid test amount');
      return;
    }

    alertActions.preview({
      budgetId: budget.id,
      testThreshold: 0.8,
      testAmountCents: Math.round(testAmount * 100)
    });
  };

  return (
    <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      <h3 className="font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
        <TestTube className="h-4 w-4" />
        Test Your Alerts
      </h3>
      
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Test Amount ($)
          </label>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={testAmountInput}
            onChange={(e) => setTestAmountInput(e.target.value)}
            placeholder="Enter test spending amount"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handlePreviewAlert}
          disabled={alertActions.isPreviewing}
          className="flex items-center gap-2"
        >
          <Eye className="h-4 w-4" />
          Preview
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleTestAlert}
          disabled={alertActions.isTesting}
          className="flex items-center gap-2"
        >
          <TestTube className="h-4 w-4" />
          Send Test
        </Button>
      </div>

      {alertActions.previewData && (
        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Alert Preview
              </p>
              <p className="text-sm text-blue-800 dark:text-blue-200 mt-1">
                {alertActions.previewData.message}
              </p>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                Priority: {alertActions.previewData.priority} | 
                Channels: {alertActions.previewData.channels.join(', ')}
              </p>
            </div>
          </div>
        </div>
      )}

      {alertActions.testData && (
        <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-start gap-2">
            <Check className="h-4 w-4 text-green-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-900 dark:text-green-100">
                Test Alert Sent!
              </p>
              <p className="text-sm text-green-800 dark:text-green-200 mt-1">
                {alertActions.testData.message}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}