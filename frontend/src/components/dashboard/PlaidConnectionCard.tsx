import React, { useState } from 'react';
import { Building2, Shield, Clock, RefreshCw, Trash2, Plus, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { PlaidLink } from '../plaid/PlaidLink';
import { useAccounts, useDeleteAccount } from '../../hooks/useAccounts';
import { usePlaidActions } from '../../hooks/usePlaid';
import type { Account } from '../../services/accountService';

interface PlaidConnectionCardProps {
  onSuccess?: () => void;
}

interface AccountItemProps {
  account: Account;
  onDelete: (accountId: string) => void;
  onSyncTransactions: (accountId?: string) => void;
  onSyncBalances: (accountId?: string) => void;
  isDeleting: boolean;
  isSyncingTransactions: boolean;
  isSyncingBalances: boolean;
}

const AccountItem: React.FC<AccountItemProps> = ({
  account,
  onDelete,
  onSyncTransactions,
  onSyncBalances,
  isDeleting,
  isSyncingTransactions,
  isSyncingBalances
}) => {
  const getStatusIcon = () => {
    if (account.connection_health === 'healthy') {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    } else if (account.connection_health === 'error') {
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
    return <Clock className="h-4 w-4 text-yellow-500" />;
  };

  const getStatusText = () => {
    switch (account.connection_health) {
      case 'healthy': return 'Connected';
      case 'error': return 'Error';
      case 'requires_update': return 'Needs Update';
      default: return 'Unknown';
    }
  };

  const formatBalance = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: account.currency || 'USD'
    }).format(cents / 100);
  };

  const isNonTransactional = ['mortgage', 'loan', 'investment', 'retirement'].includes(
    (account.account_type || '').toLowerCase()
  );
  const syncTxDisabled = isSyncingTransactions || isNonTransactional;
  const syncTxTitle = isNonTransactional
    ? 'This account type has no transaction feed. Payments show on your funding account.'
    : undefined;

  return (
    <div className="p-4 border rounded-lg bg-gray-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <Building2 className="h-5 w-5 text-gray-600" />
          <div>
            <div className="font-medium text-gray-900">{account.name}</div>
            <div className="text-sm text-gray-600 capitalize">{account.account_type.replace('_', ' ')}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-bold text-gray-900">{formatBalance(account.balance_cents)}</div>
          <div className="flex items-center space-x-1 text-xs text-gray-500">
            {getStatusIcon()}
            <span>{getStatusText()}</span>
          </div>
        </div>
      </div>

      {account.last_sync_at && (
        <div className="text-xs text-gray-500 mb-3">
          Last synced: {new Date(account.last_sync_at).toLocaleString()}
        </div>
      )}

      <div className="flex space-x-2">
        <Button
          onClick={() => onSyncTransactions(account.id)}
          disabled={syncTxDisabled}
          size="sm"
          variant="outline"
          className="flex-1"
          title={syncTxTitle}
        >
          {isSyncingTransactions ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <RefreshCw className="h-3 w-3 mr-1" />
          )}
          Sync Transactions
        </Button>
        
        <Button
          onClick={() => onSyncBalances(account.id)}
          disabled={isSyncingBalances}
          size="sm"
          variant="outline"
          className="flex-1"
        >
          {isSyncingBalances ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <RefreshCw className="h-3 w-3 mr-1" />
          )}
          Sync Balance
        </Button>

        <Button
          onClick={() => onDelete(account.id)}
          disabled={isDeleting}
          size="sm"
          variant="ghost"
          className="text-red-600 hover:text-red-700 hover:bg-red-50"
        >
          {isDeleting ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Trash2 className="h-3 w-3" />
          )}
        </Button>
      </div>
    </div>
  );
};

export const PlaidConnectionCard: React.FC<PlaidConnectionCardProps> = ({ onSuccess }) => {
  const [showModal, setShowModal] = useState(false);
  const [accountToDelete, setAccountToDelete] = useState<string | null>(null);

  // Hooks
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { mutate: deleteAccount, isPending: isDeleting } = useDeleteAccount();
  const {
    syncTransactions,
    syncBalances,
    isSyncingTransactions,
    isSyncingBalances
  } = usePlaidActions();

  const handlePlaidSuccess = () => {
    setShowModal(false);
    onSuccess?.();
  };

  const handlePlaidError = () => {
    setShowModal(false);
  };

  const handleDeleteAccount = (accountId: string) => {
    setAccountToDelete(accountId);
  };

  const confirmDelete = () => {
    if (accountToDelete) {
      deleteAccount(accountToDelete, {
        onSuccess: () => {
          setAccountToDelete(null);
        }
      });
    }
  };

  const handleSyncTransactions = (accountId?: string) => {
    syncTransactions(accountId ? { account_ids: [accountId] } : undefined);
  };

  const handleSyncBalances = (accountId?: string) => {
    syncBalances(accountId ? { account_ids: [accountId] } : undefined);
  };

  if (accountsLoading) {
    return (
      <Card className="border-2 border-blue-200">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin mr-2 text-blue-600" />
            <span className="text-blue-700">Loading accounts...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const hasAccounts = accounts && accounts.length > 0;

  return (
    <>
      <Card className="border-2 border-blue-200 bg-white">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-blue-900">
            <div className="flex items-center">
              <Building2 className="h-6 w-6 mr-3 text-blue-600" />
              Bank Account Management
            </div>
            <Button
              onClick={() => setShowModal(true)}
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Account
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {hasAccounts ? (
            <div className="space-y-4">
              <div className="text-sm text-gray-600 mb-4">
                {accounts.length} account{accounts.length !== 1 ? 's' : ''} connected
              </div>
              
              <div className="space-y-3">
                {accounts.map((account) => (
                  <AccountItem
                    key={account.id}
                    account={account}
                    onDelete={handleDeleteAccount}
                    onSyncTransactions={handleSyncTransactions}
                    onSyncBalances={handleSyncBalances}
                    isDeleting={isDeleting && accountToDelete === account.id}
                    isSyncingTransactions={isSyncingTransactions}
                    isSyncingBalances={isSyncingBalances}
                  />
                ))}
              </div>

              {accounts.length > 1 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="flex space-x-2">
                    <Button
                      onClick={() => handleSyncTransactions()}
                      disabled={isSyncingTransactions}
                      size="sm"
                      variant="outline"
                      className="flex-1"
                    >
                      {isSyncingTransactions ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3 mr-1" />
                      )}
                      Sync All Transactions
                    </Button>
                    
                    <Button
                      onClick={() => handleSyncBalances()}
                      disabled={isSyncingBalances}
                      size="sm"
                      variant="outline"
                      className="flex-1"
                    >
                      {isSyncingBalances ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3 mr-1" />
                      )}
                      Sync All Balances
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-gray-600 text-sm">
                Get started by securely connecting your bank account to automatically track transactions and balances.
              </p>
              
              <div className="flex flex-col space-y-3">
                <div className="flex items-center text-sm text-gray-600">
                  <Shield className="h-4 w-4 mr-2 text-blue-600" />
                  <span>Bank-level security with Plaid</span>
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <Clock className="h-4 w-4 mr-2 text-blue-600" />
                  <span>Instant account connection</span>
                </div>
              </div>

              <Button 
                onClick={() => setShowModal(true)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Building2 className="h-4 w-4 mr-2" />
                Connect Your First Bank Account
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Account Modal */}
      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Connect Bank Account" size="md">
        <div className="space-y-4">
          <PlaidLink onSuccess={handlePlaidSuccess} onError={handlePlaidError} />
          <Button onClick={() => setShowModal(false)} variant="ghost" size="sm" className="w-full">
            Cancel
          </Button>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal 
        isOpen={!!accountToDelete} 
        onClose={() => setAccountToDelete(null)} 
        title="Delete Account" 
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            Are you sure you want to delete this account? This will also delete all associated transactions. This action cannot be undone.
          </p>
          <div className="flex space-x-2">
            <Button
              onClick={confirmDelete}
              disabled={isDeleting}
              variant="destructive"
              className="flex-1"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : null}
              Delete Account
            </Button>
            <Button
              onClick={() => setAccountToDelete(null)}
              variant="ghost"
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};
