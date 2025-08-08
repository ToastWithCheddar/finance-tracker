// frontend/src/components/dashboard/RealtimeTransactionFeed.tsx
import React, { useEffect, useRef } from 'react';
import { 
  ArrowUpRight, 
  ArrowDownLeft, 
  Clock, 
  Building,
  Eye
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import type { RealtimeTransaction } from '../../stores/realtimeStore';
import { useRealtimeStore } from '../../stores/realtimeStore';
import { formatCurrency, formatRelativeTime } from '../../utils';

interface RealtimeTransactionFeedProps {
  transactions: RealtimeTransaction[];
  newCount: number;
}

export const RealtimeTransactionFeed: React.FC<RealtimeTransactionFeedProps> = ({
  transactions,
  newCount
}) => {
  const { markTransactionsSeen, clearOldTransactions } = useRealtimeStore();
  const feedRef = useRef<HTMLDivElement>(null);
  const prevTransactionCountRef = useRef(transactions.length);

  // Auto-scroll to top when new transactions arrive
  useEffect(() => {
    if (transactions.length > prevTransactionCountRef.current && feedRef.current) {
      feedRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    prevTransactionCountRef.current = transactions.length;
  }, [transactions.length]);

  const handleMarkSeen = () => {
    markTransactionsSeen();
  };

  const handleClearOld = () => {
    clearOldTransactions(20); // Keep only last 20
  };

  if (transactions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Recent Transactions</span>
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
              <span className="text-sm text-green-600">Live</span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Waiting for transactions...
            </h3>
            <p className="text-gray-600">
              Your real-time transactions will appear here as they happen.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            <span>Recent Transactions</span>
            {newCount > 0 && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                {newCount} new
              </span>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
              <span className="text-sm text-green-600">Live</span>
            </div>
            {newCount > 0 && (
              <Button variant="ghost" size="sm" onClick={handleMarkSeen}>
                <Eye className="h-4 w-4 mr-1" />
                Mark Seen
              </Button>
            )}
            {transactions.length > 20 && (
              <Button variant="ghost" size="sm" onClick={handleClearOld}>
                Clear Old
              </Button>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div 
          ref={feedRef}
          className="max-h-96 overflow-y-auto divide-y divide-gray-200"
        >
          {transactions.map((transaction, index) => (
            <TransactionItem 
              key={transaction.id} 
              transaction={transaction}
              isFirst={index === 0}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

interface TransactionItemProps {
  transaction: RealtimeTransaction;
  isFirst: boolean;
}

const TransactionItem: React.FC<TransactionItemProps> = ({ transaction, isFirst }) => {
  const isIncome = transaction.is_income;
  const amount = Math.abs(transaction.amountCents);
  
  return (
    <div 
      className={`p-4 hover:bg-gray-50 transition-all duration-300 ${
        transaction.isNew 
          ? 'bg-blue-50 border-l-4 border-l-blue-500 animate-pulse' 
          : ''
      } ${isFirst ? 'bg-gradient-to-r from-blue-50 to-transparent' : ''}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {/* Transaction Type Icon */}
          <div className={`p-2 rounded-full ${
            isIncome 
              ? 'bg-green-100 text-green-600' 
              : 'bg-red-100 text-red-600'
          }`}>
            {isIncome ? (
              <ArrowDownLeft className="h-4 w-4" />
            ) : (
              <ArrowUpRight className="h-4 w-4" />
            )}
          </div>

          {/* Transaction Details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-gray-900 truncate">
                {transaction.description}
              </h4>
              <span className={`font-semibold ${
                isIncome ? 'text-green-600' : 'text-gray-900'
              }`}>
                {isIncome ? '+' : '-'}{formatCurrency(amount)}
              </span>
            </div>
            
            <div className="flex items-center justify-between mt-1">
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                {/* Category */}
                {transaction.category_name && (
                  <div className="flex items-center">
                    {transaction.category_emoji && (
                      <span className="mr-1">{transaction.category_emoji}</span>
                    )}
                    <span>{transaction.category_name}</span>
                  </div>
                )}
                
                {/* Merchant */}
                {transaction.merchant && (
                  <>
                    <span>•</span>
                    <div className="flex items-center">
                      <Building className="h-3 w-3 mr-1" />
                      <span>{transaction.merchant}</span>
                    </div>
                  </>
                )}
                
                {/* Account */}
                {transaction.account_name && (
                  <>
                    <span>•</span>
                    <span>{transaction.account_name}</span>
                  </>
                )}
              </div>
              
              {/* Timestamp */}
              <div className="text-xs text-gray-400">
                {formatRelativeTime(transaction.created_at || transaction.createdAt)}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* New Transaction Badge */}
      {transaction.isNew && (
        <div className="mt-2 flex justify-end">
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1 animate-pulse"></div>
            New
          </span>
        </div>
      )}
    </div>
  );
};

export default RealtimeTransactionFeed;