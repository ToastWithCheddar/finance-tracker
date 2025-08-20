import { useState, useEffect } from 'react';
import { RefreshCw, WifiOff } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { useWebSocket, type WebSocketMessage } from '../../hooks/useWebSocket';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { formatLastSync } from '../../utils/date';
import { getConnectionStatusIcon, getConnectionStatusText, getConnectionStatusColor } from '../../utils/account';
import { useAccountSyncStatus } from '../../hooks/useAccountSyncStatus';


interface AccountSyncStatusProps {
  refreshTrigger?: number;
  onSyncComplete?: () => void;
}

export function AccountSyncStatus({ refreshTrigger = 0, onSyncComplete }: AccountSyncStatusProps) {
  const [syncing, setSyncing] = useState(false);
  const {
    connectionStatus,
    isLoadingConnectionStatus,
    connectionStatusError,
    refetchConnectionStatus,
    syncAllBalances,
    isSyncingAllBalances,
    syncAccountBalance,
    isSyncingAccountBalance
  } = useAccountSyncStatus();

  // Listen for real-time updates
  useWebSocket({
    onMessage: (msg: WebSocketMessage) => {
      const event = { type: msg.type, data: msg.payload };
      if (event.type === 'ACCOUNT_BALANCE_UPDATED' || event.type === 'ACCOUNT_CONNECTED') {
        refetchConnectionStatus();
        onSyncComplete?.();
      }
    }
  });


  const handleSyncAll = async () => {
    try {
      setSyncing(true);
      await syncAllBalances();
      onSyncComplete?.();
    } catch (err) {
      console.error('Sync all failed:', err);
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncAccount = async (accountId: string) => {
    try {
      setSyncing(true);
      await syncAccountBalance(accountId);
      onSyncComplete?.();
    } catch (err) {
      console.error('Sync account failed:', err);
    } finally {
      setSyncing(false);
    }
  };


  useEffect(() => {
    refetchConnectionStatus();
  }, [refreshTrigger, refetchConnectionStatus]);

  if (isLoadingConnectionStatus) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center">
          <LoadingSpinner size="md" />
          <span className="ml-2 text-gray-600">Loading connection status...</span>
        </div>
      </Card>
    );
  }

  if (connectionStatusError) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <XCircle className="h-5 w-5 text-red-500 mr-2" />
            <span className="text-red-600">{connectionStatusError.message}</span>
          </div>
          <Button onClick={() => refetchConnectionStatus()} variant="outline" size="sm">
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  if (!connectionStatus) {
    return (
      <Card className="p-6">
        <div className="text-center text-gray-500">
          <WifiOff className="h-12 w-12 mx-auto mb-2 text-gray-400" />
          <p>No connected accounts found</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Account Connections</h3>
            <p className="text-sm text-gray-600">
              {connectionStatus.active_connections} of {connectionStatus.total_connections} accounts syncing properly
            </p>
          </div>
          <Button
            onClick={handleSyncAll}
            disabled={syncing || connectionStatus.total_connections === 0}
            className="flex items-center"
          >
            {syncing ? (
              <LoadingSpinner size="sm" className="mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Sync All
          </Button>
        </div>

        {/* Connection Summary Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{connectionStatus.active_connections}</div>
            <div className="text-sm text-gray-600">Healthy</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {connectionStatus.total_connections - connectionStatus.active_connections - connectionStatus.failed_connections}
            </div>
            <div className="text-sm text-gray-600">Warning</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{connectionStatus.failed_connections}</div>
            <div className="text-sm text-gray-600">Failed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{connectionStatus.needs_reauth}</div>
            <div className="text-sm text-gray-600">Need Reauth</div>
          </div>
        </div>
      </Card>

      {/* Individual Account Status */}
      <div className="space-y-3">
        {connectionStatus.accounts.map((account) => (
          <Card key={account.account_id} className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {getConnectionStatusIcon(account.health_status)}
                <div>
                  <h4 className="font-medium text-gray-900">{account.name}</h4>
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <span className="capitalize">{account.type.replace('_', ' ')}</span>
                    <span>•</span>
                    <span className={`px-2 py-1 rounded-full text-xs ${getConnectionStatusColor(account.health_status)}`}>
                      {getConnectionStatusText(account.health_status)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <div className="font-semibold text-gray-900">
                    {new Intl.NumberFormat('en-US', {
                      style: 'currency',
                      currency: account.currency
                    }).format(account.balance)}
                  </div>
                  <div className="text-sm text-gray-500">
                    Last sync: {formatLastSync(account.last_sync)}
                  </div>
                </div>

                <Button
                  onClick={() => handleSyncAccount(account.account_id)}
                  disabled={syncing}
                  variant="outline"
                  size="sm"
                >
                  {syncing ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {connectionStatus.accounts.length === 0 && (
        <Card className="p-8">
          <div className="text-center">
            <WifiOff className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Connected Accounts</h3>
            <p className="text-gray-600 mb-4">
              Connect your bank accounts to automatically sync balances and transactions.
            </p>
            <Button variant="primary">
              Connect Bank Account
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}