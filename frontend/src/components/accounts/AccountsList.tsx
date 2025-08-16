import { useState, useMemo } from 'react';
import { useAccounts } from '../../hooks/useAccounts';
import { usePlaidActions } from '../../hooks/usePlaid';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { 
  Building2, 
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  PiggyBank,
  TrendingUp,
  Wallet,
  Banknote,
  CreditCard
} from 'lucide-react';
import { accountService } from '../../services/accountService';
import { PlaidLink } from '../plaid/PlaidLink';

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

  // Calculate totals
  const totals = useMemo(() => {
    return displayAccounts.reduce(
      (acc, account) => {
        acc.total += account.balance_cents;
        if (account.balance_cents > 0) acc.assets += account.balance_cents;
        else acc.liabilities += Math.abs(account.balance_cents);
        return acc;
      },
      { total: 0, assets: 0, liabilities: 0 }
    );
  }, [displayAccounts]);

  // Modal handlers
  const openModal = () => setShowModal(true);
  const closeModal = () => setShowModal(false);

  const handlePlaidSuccess = () => {
    closeModal();
    refetch();
  };

  // Account icon helper
  const getAccountIcon = (accountType: string) => {
    switch (accountType) {
      case 'checking': return <Banknote className="h-5 w-5 text-blue-600" />;
      case 'savings': return <PiggyBank className="h-5 w-5 text-green-600" />;
      case 'credit_card': return <CreditCard className="h-5 w-5 text-red-600" />;
      case 'investment': return <TrendingUp className="h-5 w-5 text-purple-600" />;
      default: return <Wallet className="h-5 w-5 text-gray-600" />;
    }
  };

  // Health icon helper
  const getHealthIcon = (health?: string) => {
    switch (health) {
      case 'healthy': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'failed': return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default: return <Clock className="h-4 w-4 text-gray-400" />;
    }
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
        {showModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Connect Bank Account</h3>
              <PlaidLink onSuccess={handlePlaidSuccess} onError={closeModal} />
              <Button onClick={closeModal} variant="ghost" size="sm" className="mt-4 w-full">
                Cancel
              </Button>
            </div>
          </div>
        )}
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
        <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <div className="text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Net Worth</p>
            <p className={`font-semibold ${totals.total >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {accountService.formatBalance(totals.total)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Assets</p>
            <p className="font-semibold text-green-600">
              {accountService.formatBalance(totals.assets)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Liabilities</p>
            <p className="font-semibold text-red-600">
              {accountService.formatBalance(totals.liabilities)}
            </p>
          </div>
        </div>

        {/* Accounts List */}
        <div className="space-y-3">
          {displayAccounts.map((account) => (
            <div
              key={account.id}
              className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg hover:shadow-md transition-shadow"
            >
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {getAccountIcon(account.account_type)}
                </div>
                
                <div className="min-w-0 flex-1">
                  <div className="flex items-center space-x-2">
                    <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {account.name}
                    </p>
                    {account.plaid_account_id && getHealthIcon(account.connection_health)}
                  </div>
                  
                  <div className="flex items-center space-x-2 mt-1">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {accountService.getAccountTypeLabel(account.account_type)}
                    </p>
                    
                    {account.plaid_account_id && (
                      <>
                        <span className="text-gray-300">•</span>
                        <p className={`text-xs ${accountService.getConnectionHealthColor(account.connection_health)}`}>
                          {accountService.getConnectionHealthLabel(account.connection_health)}
                        </p>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <p className={`font-semibold ${account.balance_cents >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {accountService.formatBalance(account.balance_cents)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {account.currency}
                </p>
                {account.last_sync_at && (
                  <p className="text-xs text-gray-400">
                    Synced {new Date(account.last_sync_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
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
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Connect Bank Account</h3>
            <PlaidLink onSuccess={handlePlaidSuccess} onError={closeModal} />
            <Button onClick={closeModal} variant="ghost" size="sm" className="mt-4 w-full">
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}