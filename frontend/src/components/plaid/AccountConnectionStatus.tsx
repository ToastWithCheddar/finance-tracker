import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { PlaidLink } from './PlaidLink';
import { usePlaidConnectionStatus, usePlaidActions } from '../../hooks/usePlaid';
import { plaidService } from '../../services/plaidService';
import { 
  Building2, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle,
  CreditCard,
  Banknote
} from 'lucide-react';

export function AccountConnectionStatus() {
  const [showPlaidLink, setShowPlaidLink] = useState(false);
  const [isQuickLinking, setIsQuickLinking] = useState(false);
  
  const { data: connectionStatus, isLoading, error, refetch } = usePlaidConnectionStatus();
  const { 
    syncTransactions, 
    syncBalances, 
    isSyncingTransactions, 
    isSyncingBalances,
    syncTransactionsResult,
    syncBalancesResult 
  } = usePlaidActions();

  const handlePlaidSuccess = (accounts: unknown[]) => {
    console.log('✅ Successfully connected accounts:', accounts);
    setShowPlaidLink(false);
    // Refetch connection status
    refetch();
  };

  const handleSyncTransactions = () => {
    syncTransactions(undefined);
  };

  const handleSyncBalances = () => {
    syncBalances(undefined);
  };

  const handleQuickSandboxLink = async () => {
    try {
      setIsQuickLinking(true);
      await plaidService.quickSandboxLink();
      await refetch();
    } catch (e) {
      console.error('Quick sandbox link failed:', e);
    } finally {
      setIsQuickLinking(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(cents / 100);
  };

  const getAccountIcon = (type: string | undefined | null) => {
    const accountType = type?.toLowerCase() || 'unknown';
    switch (accountType) {
      case 'credit':
      case 'credit_card':
        return <CreditCard className="h-5 w-5" />;
      case 'checking':
      case 'savings':
      default:
        return <Banknote className="h-5 w-5" />;
    }
  };

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  if (isLoading) {
    return (
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-center">
            <LoadingSpinner size="sm" className="mr-2" />
            <span>Checking account connections...</span>
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <div className="p-6">
          <div className="flex items-center text-red-600">
            <AlertTriangle className="h-5 w-5 mr-2" />
            <span>Failed to load account status</span>
          </div>
          <Button
            onClick={() => refetch()}
            variant="outline"
            size="sm"
            className="mt-3"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Bank Accounts</h3>
            <Button
              onClick={() => refetch()}
              variant="ghost"
              size="sm"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {!connectionStatus?.connected ? (
            <div className="text-center py-8">
              <Building2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">
                No Bank Accounts Connected
              </h4>
              <p className="text-gray-500 mb-6">
                Connect your bank account to automatically import transactions and track your finances.
              </p>
              
              <Button
                onClick={() => setShowPlaidLink(true)}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Building2 className="h-4 w-4 mr-2" />
                Connect First Account
              </Button>

              {import.meta.env.DEV && (
                <div className="mt-3">
                  <Button
                    onClick={handleQuickSandboxLink}
                    variant="outline"
                    size="sm"
                    disabled={isQuickLinking}
                  >
                    {isQuickLinking ? (
                      <>
                        <LoadingSpinner size="xs" className="mr-2" />
                        Linking Sandbox...
                      </>
                    ) : (
                      <>
                        <Building2 className="h-4 w-4 mr-2" />
                        Quick Sandbox Link
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Connected Accounts */}
              <div className="grid gap-4">
                {connectionStatus.accounts.map((account) => (
                  <div
                    key={account.id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      {getAccountIcon(account.account_type)}
                      <div>
                        <h4 className="font-medium text-gray-900">{account.name || 'Unknown Account'}</h4>
                        <p className="text-sm text-gray-500 capitalize">
                          {account.account_type?.replace('_', ' ') || 'Unknown'}
                        </p>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="font-medium text-gray-900">
                        {formatCurrency(account.balance_cents || 0)}
                      </div>
                      <div className="flex items-center space-x-2 mt-1">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getHealthColor(
                            account.connection_health || 'unknown'
                          )}`}
                        >
                          {account.connection_health || 'unknown'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {account.sync_status || 'unknown'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Sync Controls */}
              <div className="border-t pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900">Sync Data</h4>
                    <p className="text-sm text-gray-500">
                      Keep your transactions and balances up to date
                    </p>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button
                      onClick={handleSyncTransactions}
                      disabled={isSyncingTransactions}
                      variant="outline"
                      size="sm"
                    >
                      {isSyncingTransactions ? (
                        <LoadingSpinner size="xs" className="mr-2" />
                      ) : (
                        <RefreshCw className="h-4 w-4 mr-2" />
                      )}
                      Sync Transactions
                    </Button>
                    
                    <Button
                      onClick={handleSyncBalances}
                      disabled={isSyncingBalances}
                      variant="outline"
                      size="sm"
                    >
                      {isSyncingBalances ? (
                        <LoadingSpinner size="xs" className="mr-2" />
                      ) : (
                        <RefreshCw className="h-4 w-4 mr-2" />
                      )}
                      Sync Balances
                    </Button>
                  </div>
                </div>

                {/* Sync Results */}
                {syncTransactionsResult && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                    <CheckCircle className="h-4 w-4 inline mr-1" />
                    {syncTransactionsResult.message}
                  </div>
                )}

                {syncBalancesResult && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                    <CheckCircle className="h-4 w-4 inline mr-1" />
                    {syncBalancesResult.message}
                  </div>
                )}
              </div>

              {/* Add Another Account */}
              <div className="border-t pt-4">
                <Button
                  onClick={() => setShowPlaidLink(true)}
                  variant="outline"
                  size="sm"
                >
                  <Building2 className="h-4 w-4 mr-2" />
                  Add Another Account
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>

      <Modal isOpen={showPlaidLink} onClose={() => setShowPlaidLink(false)} title="Connect Bank Account" size="sm">
        <PlaidLink
          key="plaid-link-component"
          onSuccess={handlePlaidSuccess}
          onError={() => setShowPlaidLink(false)}
        />
        <Button
          onClick={() => setShowPlaidLink(false)}
          variant="ghost"
          size="sm"
          className="mt-4 w-full"
        >
          Cancel
        </Button>
      </Modal>
    </div>
  );
}