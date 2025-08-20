import { useState, useMemo } from 'react';
import { useAccounts } from '../../hooks/useAccounts';
import { usePlaidActions } from '../../hooks/usePlaid';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { Building2, RefreshCw } from 'lucide-react';
import { AccountTotals } from './AccountTotals';
import { AccountListItem } from './AccountListItem';
import { AddAccountModal } from './AddAccountModal';

interface AccountsListProps {
  className?: string;
  showTitle?: boolean;
}

export function AccountsList({ className = '', showTitle = true }: AccountsListProps) {
  const [showModal, setShowModal] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'all' | 'plaid' | 'manual'>('all');
  
  // Single data source
  const { data: accounts, isLoading, error, refetch } = useAccounts();
  const { syncBalances, syncTransactions, isSyncingBalances, isSyncingTransactions } = usePlaidActions();

  // Derive filtered data locally
  const { plaidAccounts, manualAccounts, displayAccounts } = useMemo(() => {
    const plaid = accounts?.filter(account => !!account.plaid_account_id) || [];
    const manual = accounts?.filter(account => !account.plaid_account_id) || [];
    
    let display = accounts || [];
    if (selectedTab === 'plaid') display = plaid;
    else if (selectedTab === 'manual') display = manual;

    return {
      plaidAccounts: plaid,
      manualAccounts: manual,
      displayAccounts: display
    };
  }, [accounts, selectedTab]);


  // Modal handlers
  const openModal = () => setShowModal(true);
  const closeModal = () => setShowModal(false);

  const handleAccountAdded = () => {
    refetch();
  };



  if (isLoading) {
    return (
      <Card className={className}>
        {showTitle && (
          <CardHeader>
            <CardTitle className="flex items-center">
              <Building2 className="h-5 w-5 mr-2" />
              Accounts
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        {showTitle && (
          <CardHeader>
            <CardTitle className="flex items-center">
              <Building2 className="h-5 w-5 mr-2" />
              Accounts
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 mb-2">Failed to load accounts</p>
              <Button onClick={() => refetch()} size="sm" variant="outline">
                Try Again
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!accounts?.length) {
    return (
      <Card className={className}>
        {showTitle && (
          <CardHeader>
            <CardTitle className="flex items-center">
              <Building2 className="h-5 w-5 mr-2" />
              Accounts
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="text-center py-8">
            <Building2 className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p className="mb-2 text-gray-600">No accounts found</p>
            <p className="text-sm mb-4 text-gray-500">Connect your bank account to get started</p>
            <Button onClick={openModal} className="bg-blue-600 hover:bg-blue-700">
              <Building2 className="h-4 w-4 mr-2" />
              Connect Bank Account
            </Button>
          </div>
        </CardContent>

        {/* Modal */}
        <AddAccountModal
          isOpen={showModal}
          onClose={closeModal}
          onSuccess={handleAccountAdded}
        />
      </Card>
    );
  }

  return (
    <Card className={className}>
      {showTitle && (
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center">
              <Building2 className="h-5 w-5 mr-2" />
              Accounts
            </CardTitle>
          </div>

          {/* Tabs */}
          <div className="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
            <button
              onClick={() => setSelectedTab('all')}
              className={`flex-1 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                selectedTab === 'all'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              All ({accounts?.length || 0})
            </button>
            <button
              onClick={() => setSelectedTab('plaid')}
              className={`flex-1 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                selectedTab === 'plaid'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              Connected ({plaidAccounts.length})
            </button>
            <button
              onClick={() => setSelectedTab('manual')}
              className={`flex-1 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                selectedTab === 'manual'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
              }`}
            >
              Manual ({manualAccounts.length})
            </button>
          </div>
        </CardHeader>
      )}
      
      <CardContent>
        {/* Totals */}
        <AccountTotals accounts={displayAccounts} className="mb-6" />

        {/* Accounts List */}
        <div className="space-y-3">
          {displayAccounts.map((account) => (
            <AccountListItem key={account.id} account={account} />
          ))}
        </div>

        {/* Bottom actions: Add account and Sync buttons */}
        <div className="border-t pt-4 mt-6 flex flex-wrap items-center justify-between gap-2">
          <Button onClick={openModal} variant="outline" size="sm">
            <Building2 className="h-4 w-4 mr-2" />
            Add Another Account
          </Button>
          <div className="flex gap-2">
            <Button 
              onClick={() => syncTransactions(undefined)} 
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
              onClick={() => syncBalances(undefined)} 
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
      </CardContent>

      {/* Modal */}
      <AddAccountModal
        isOpen={showModal}
        onClose={closeModal}
        onSuccess={handleAccountAdded}
      />
    </Card>
  );
}