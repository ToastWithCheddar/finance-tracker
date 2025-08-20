import { useMemo } from 'react';
import { accountService } from '../../services/accountService';
import type { Account } from '../../services/accountService';

interface AccountTotalsProps {
  accounts: Account[];
  className?: string;
}

interface TotalsData {
  total: number;
  assets: number;
  liabilities: number;
}

export function AccountTotals({ accounts, className = '' }: AccountTotalsProps) {
  // Calculate totals from accounts
  const totals = useMemo<TotalsData>(() => {
    return accounts.reduce(
      (acc, account) => {
        acc.total += account.balance_cents;
        if (account.balance_cents > 0) acc.assets += account.balance_cents;
        else acc.liabilities += Math.abs(account.balance_cents);
        return acc;
      },
      { total: 0, assets: 0, liabilities: 0 }
    );
  }, [accounts]);

  return (
    <div className={`grid grid-cols-3 gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg ${className}`}>
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
  );
}

export type { TotalsData };