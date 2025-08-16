import { useState, useEffect, useCallback } from 'react';
import { CheckCircle, AlertTriangle, XCircle, Calculator, DollarSign, TrendingUp } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { apiClient } from '../../services/api';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useWebSocket, type WebSocketMessage } from '../../hooks/useWebSocket';

interface ReconciliationResult {
  account_id: string;
  account_name: string;
  recorded_balance: number;
  calculated_balance: number;
  discrepancy: number;
  discrepancy_cents: number;
  is_reconciled: boolean;
  reconciliation_threshold: number;
  transaction_count: number;
  reconciliation_date: string;
  suggestions: string[];
}

interface AccountReconciliationProps {
  accountId: string;
  onReconciliationComplete?: () => void;
}

export function AccountReconciliation({ accountId, onReconciliationComplete }: AccountReconciliationProps) {
  const [reconciliation, setReconciliation] = useState<ReconciliationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdjustmentModal, setShowAdjustmentModal] = useState(false);
  const [adjustmentAmount, setAdjustmentAmount] = useState('');
  const [adjustmentDescription, setAdjustmentDescription] = useState('');
  const [submittingAdjustment, setSubmittingAdjustment] = useState(false);

  // Listen for real-time reconciliation updates
  useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      if (message.type === 'ACCOUNT_RECONCILED' && message.payload.account_id === accountId) {
        setReconciliation(prev => prev ? { ...prev, ...message.payload } : null);
        onReconciliationComplete?.();
      }
    }
  });

  const performReconciliation = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.post<{ success: boolean; data: ReconciliationResult }>(
        `/api/accounts/${accountId}/reconcile`
      );
      
      if (response.success) {
        setReconciliation(response.data);
        onReconciliationComplete?.();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reconcile account');
    } finally {
      setLoading(false);
    }
  }, [accountId, onReconciliationComplete]);

  const handleCreateAdjustment = async () => {
    if (!adjustmentAmount || !adjustmentDescription.trim()) return;

    try {
      setSubmittingAdjustment(true);
      
      const adjustmentCents = Math.round(parseFloat(adjustmentAmount) * 100);
      
      const response = await apiClient.post<{ success: boolean; data: Record<string, unknown> }>(
        `/api/accounts/${accountId}/reconciliation-entry`,
        {
          adjustment_cents: adjustmentCents,
          description: adjustmentDescription
        }
      );
      
      if (response.success) {
        setShowAdjustmentModal(false);
        setAdjustmentAmount('');
        setAdjustmentDescription('');
        // Re-run reconciliation to get updated status
        await performReconciliation();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create adjustment');
    } finally {
      setSubmittingAdjustment(false);
    }
  };

  const getStatusIcon = (isReconciled: boolean, discrepancy: number) => {
    if (isReconciled) {
      return <CheckCircle className="h-6 w-6 text-green-500" />;
    } else if (Math.abs(discrepancy) < 10) {
      return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
    } else {
      return <XCircle className="h-6 w-6 text-red-500" />;
    }
  };

  const getStatusColor = (isReconciled: boolean, discrepancy: number) => {
    if (isReconciled) {
      return 'text-green-600 bg-green-50 border-green-200';
    } else if (Math.abs(discrepancy) < 10) {
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    } else {
      return 'text-red-600 bg-red-50 border-red-200';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  useEffect(() => {
    if (accountId) {
      performReconciliation();
    }
  }, [accountId, performReconciliation]);

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Calculator className="h-5 w-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Account Reconciliation</h3>
          </div>
          <Button
            onClick={performReconciliation}
            disabled={loading}
            variant="outline"
            size="sm"
          >
            {loading ? <LoadingSpinner size="sm" /> : 'Reconcile'}
          </Button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        {loading && !reconciliation && (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="md" />
            <span className="ml-2 text-gray-600">Reconciling account...</span>
          </div>
        )}

        {reconciliation && (
          <div className="space-y-4">
            {/* Status Overview */}
            <div className={`p-4 rounded-lg border ${getStatusColor(reconciliation.is_reconciled, reconciliation.discrepancy)}`}>
              <div className="flex items-center space-x-3">
                {getStatusIcon(reconciliation.is_reconciled, reconciliation.discrepancy)}
                <div>
                  <h4 className="font-medium">
                    {reconciliation.is_reconciled ? 'Account Reconciled' : 'Discrepancy Detected'}
                  </h4>
                  <p className="text-sm opacity-75">
                    {reconciliation.is_reconciled 
                      ? 'Your account balance matches the calculated balance from transactions'
                      : `Discrepancy of ${formatCurrency(Math.abs(reconciliation.discrepancy))} detected`
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
                  {formatCurrency(reconciliation.recorded_balance)}
                </div>
                <div className="text-sm text-gray-600">Recorded Balance</div>
              </div>

              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <Calculator className="h-6 w-6 text-gray-600 mx-auto mb-2" />
                <div className="text-lg font-semibold text-gray-900">
                  {formatCurrency(reconciliation.calculated_balance)}
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
                   (reconciliation.discrepancy > 0 ? '+' : '') + formatCurrency(reconciliation.discrepancy)
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
              disabled={!adjustmentAmount || !adjustmentDescription.trim() || submittingAdjustment}
              variant="primary"
              className="flex-1"
            >
              {submittingAdjustment ? <LoadingSpinner size="sm" /> : 'Create Adjustment'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}