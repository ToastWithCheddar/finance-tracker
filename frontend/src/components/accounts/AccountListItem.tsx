import { accountService } from '../../services/accountService';
import { getAccountIcon, getHealthIcon } from '../../utils/account';
import type { Account } from '../../services/accountService';

interface AccountListItemProps {
  account: Account;
  className?: string;
}

export function AccountListItem({ account, className = '' }: AccountListItemProps) {
  return (
    <div
      className={`flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg hover:shadow-md transition-shadow ${className}`}
    >
      <div className="flex items-center space-x-3">
        <div className="flex-shrink-0">
          {getAccountIcon(account.account_type, true)}
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
  );
}