import React, { useState, useCallback } from 'react';
import { Calculator, DollarSign, TrendingUp } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useWebSocket, type WebSocketMessage } from '../../hooks/useWebSocket';
import { CurrencyUtils } from '../../utils/currency';
import { getReconciliationStatusIcon, getReconciliationStatusColor } from '../../utils/account';
import { useAccountReconciliation, type ReconciliationResult } from '../../hooks/useAccountReconciliation';


interface AccountReconciliationProps {
  accountId: string;
  onReconciliationComplete?: () => void;
}

export function AccountReconciliation({ accountId, onReconciliationComplete }: AccountReconciliationProps) {
  const [reconciliation, setReconciliation] = useState<ReconciliationResult | null>(null);
  const {
    performReconciliation,
    isPerformingReconciliation,
    reconciliationError,
    createAdjustment,
    isCreatingAdjustment,
    adjustmentError,
    resetReconciliationError,
    resetAdjustmentError
  } = useAccountReconciliation();
  const [showAdjustmentModal, setShowAdjustmentModal] = useState(false);
  const [adjustmentAmount, setAdjustmentAmount] = useState('');
  const [adjustmentDescription, setAdjustmentDescription] = useState('');

  // Listen for real-time reconciliation updates
  useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      if (message.type === 'ACCOUNT_RECONCILED' && message.payload.account_id === accountId) {
        setReconciliation(prev => prev ? { ...prev, ...message.payload } : null);
        onReconciliationComplete?.();
      }
    }
  });

  const handlePerformReconciliation = useCallback(async () => {
    try {
      resetReconciliationError();
      const result = await performReconciliation(accountId);
      setReconciliation(result);
      onReconciliationComplete?.();
    } catch (err) {
      // Error is handled by the hook
      console.error('Reconciliation failed:', err);
    }
  }, [accountId, performReconciliation, resetReconciliationError, onReconciliationComplete]);

  const handleCreateAdjustment = async () => {
    if (!adjustmentAmount || !adjustmentDescription.trim()) return;

    try {
      resetAdjustmentError();
      
      const adjustmentCents = Math.round(parseFloat(adjustmentAmount) * 100);
      
      await createAdjustment({
        accountId,
        adjustmentData: {
          adjustment_cents: adjustmentCents,
          description: adjustmentDescription
        }
      });
      
      setShowAdjustmentModal(false);
      setAdjustmentAmount('');
      setAdjustmentDescription('');
      // Re-run reconciliation to get updated status
      await handlePerformReconciliation();
    } catch (err) {
      // Error is handled by the hook
      console.error('Adjustment creation failed:', err);
    }
  };


  // Auto-perform reconciliation when account changes
  React.useEffect(() => {
    if (accountId) {
      handlePerformReconciliation();
    }
  }, [accountId, handlePerformReconciliation]);

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Calculator className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Account Reconciliation</h3>
          </div>
          <Button
            onClick={handlePerformReconciliation}
            disabled={isPerformingReconciliation}
            variant="outline"
            size="sm"
          >
            {isPerformingReconciliation ? <LoadingSpinner size="sm" /> : 'Reconcile'}
          </Button>
        </div>

        {(reconciliationError || adjustmentError) && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">
              {reconciliationError?.message || adjustmentError?.message}
            </p>
          </div>
        )}

        {isPerformingReconciliation && !reconciliation && (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="md" />
            <span className="ml-2 text-gray-600">Reconciling account...</span>
          </div>
        )}

        {reconciliation && (
          <div className="space-y-4">
            {/* Status Overview */}
            <div className={`p-4 rounded-lg border ${getReconciliationStatusColor(reconciliation.is_reconciled, reconciliation.discrepancy)}`}>
              <div className="flex items-center space-x-3">
                {getReconciliationStatusIcon(reconciliation.is_reconciled, reconciliation.discrepancy)}
                <div>
                  <h4 className="font-medium">
                    {reconciliation.is_reconciled ? 'Account Reconciled' : 'Discrepancy Detected'}
                  </h4>
                  <p className="text-sm opacity-75">
                    {reconciliation.is_reconciled 
                      ? 'Your account balance matches the calculated balance from transactions'
                      : `Discrepancy of ${CurrencyUtils.formatDollars(Math.abs(reconciliation.discrepancy))} detected`
                    }
                  </p>
                </div>
              </div>
            </div>

            {/* Balance Details */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <DollarSign className="h-6 w-6 text-gray-600 mx-auto mb-2" />
                <div className="text-lg font-semibold text-gray-900">
                  {CurrencyUtils.formatDollars(reconciliation.recorded_balance)}
                </div>
                <div className="text-sm text-gray-600">Recorded Balance</div>
              </div>

              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <Calculator className="h-6 w-6 text-gray-600 mx-auto mb-2" />
                <div className="text-lg font-semibold text-gray-900">
                  {CurrencyUtils.formatDollars(reconciliation.calculated_balance)}
                </div>
                <div className="text-sm text-gray-600">Calculated Balance</div>
              </div>

              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <TrendingUp className="h-6 w-6 text-gray-600 mx-auto mb-2" />
                <div className={`text-lg font-semibold ${
                  reconciliation.discrepancy === 0 ? 'text-green-600' : 
                  reconciliation.discrepancy > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {reconciliation.discrepancy === 0 ? '—' : 
                   (reconciliation.discrepancy > 0 ? '+' : '') + CurrencyUtils.formatDollars(reconciliation.discrepancy)
                  }
                </div>
                <div className="text-sm text-gray-600">Discrepancy</div>
              </div>
            </div>

            {/* Transaction Count */}
            <div className="flex items-center justify-center text-sm text-gray-600">
              <span>Based on {reconciliation.transaction_count} transactions</span>
              <span className="mx-2">•</span>
              <span>Last reconciled: {new Date(reconciliation.reconciliation_date).toLocaleString()}</span>
            </div>

            {/* Suggestions */}
            {reconciliation.suggestions.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h5 className="font-medium text-blue-900 mb-2">Reconciliation Suggestions</h5>
                <ul className="space-y-1 text-sm text-blue-800">
                  {reconciliation.suggestions.slice(0, 5).map((suggestion, index) => (
                    <li key={index} className="flex items-start">
                      <span className="mr-2">•</span>
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Action Buttons */}
            {!reconciliation.is_reconciled && (
              <div className="flex space-x-3">
                <Button
                  onClick={() => setShowAdjustmentModal(true)}
                  variant="primary"
                  className="flex-1"
                >
                  Create Adjustment Entry
                </Button>
                <Button
                  onClick={performReconciliation}
                  variant="outline"
                  className="flex-1"
                >
                  Re-reconcile
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Adjustment Modal */}
      <Modal
        isOpen={showAdjustmentModal}
        onClose={() => setShowAdjustmentModal(false)}
        title="Create Reconciliation Adjustment"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            Create a manual adjustment to reconcile the balance discrepancy. This will add a transaction
            to bring your calculated balance in line with your actual account balance.
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Adjustment Amount
            </label>
            <Input
              type="number"
              step="0.01"
              placeholder="0.00"
              value={adjustmentAmount}
              onChange={(e) => setAdjustmentAmount(e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter positive amount to increase balance, negative to decrease
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <Input
              type="text"
              placeholder="e.g., Bank fee adjustment, Missing deposit, etc."
              value={adjustmentDescription}
              onChange={(e) => setAdjustmentDescription(e.target.value)}
            />
          </div>

          <div className="flex space-x-3">
            <Button
              onClick={() => setShowAdjustmentModal(false)}
              variant="outline"
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateAdjustment}
              disabled={!adjustmentAmount || !adjustmentDescription.trim() || isCreatingAdjustment}
              variant="primary"
              className="flex-1"
            >
              {isCreatingAdjustment ? <LoadingSpinner size="sm" /> : 'Create Adjustment'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}