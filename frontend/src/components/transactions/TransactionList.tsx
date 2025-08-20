import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { TransactionItem } from './TransactionItem';
import { formatCurrency, formatGroupDate, getCategoryColor, getAmountColor } from '../../utils';
import type { Transaction, TransactionStats, TransactionGroup, TransactionGroupedResponse } from '../../types/transaction';

// Legacy grouped data format - kept for backward compatibility
// This interface supports parent components that haven't migrated to TransactionGroup[] yet
interface GroupedTransactions {
  [date: string]: {
    transactions: Transaction[];
    total: number; // Net total in cents for the day
  };
}

interface TransactionListProps {
  /**
   * @deprecated Use 'groups' prop instead. This legacy prop is maintained for backward compatibility.
   * Legacy grouped data format - will be removed in a future version.
   * 
   * Migration path:
   * 1. Replace 'groupedTransactions' prop with 'groups' prop
   * 2. Update parent components to use TransactionGroup[] format
   * 3. Use the new format which provides better type safety and performance
   * 
   * @see groups - The new preferred format
   */
  groupedTransactions?: GroupedTransactions;
  /**
   * Preferred format for grouped transaction data.
   * Provides better type safety, performance, and consistency across the application.
   */
  groups?: TransactionGroup[];
  expandedGroups: Set<string>;
  onToggleGroup: (key: string) => void;
  stats?: TransactionStats;
  isLoading?: boolean;
  onEdit: (transaction: Transaction) => void;
  onDelete: (transactionId: string) => void;
  onBulkDelete: (transactionIds: string[]) => void;
  groupType?: 'date' | 'category' | 'merchant' | 'none';
}

export function TransactionList({ 
  groupedTransactions,
  groups,
  expandedGroups,
  onToggleGroup,
  stats,
  isLoading = false,
  onEdit, 
  onDelete,
  onBulkDelete,
  groupType = 'date'
}: TransactionListProps) {
  const [selectedTransactions, setSelectedTransactions] = useState<string[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; transactionId?: string }>({
    isOpen: false
  });
  
  // Deprecation warning for legacy prop usage
  if (process.env.NODE_ENV === 'development' && groupedTransactions && !groups) {
    console.warn(
      '⚠️  TransactionList: The "groupedTransactions" prop is deprecated. ' +
      'Please migrate to the "groups" prop for better type safety and performance. ' +
      'See component documentation for migration guide.'
    );
  }
  
  /**
   * Legacy format conversion for backward compatibility
   * TODO: Remove this conversion once all parent components migrate to 'groups' prop
   * 
   * This conversion maintains backward compatibility while parent components
   * are gradually updated to use the new TransactionGroup[] format.
   */
  const normalizedGroups: TransactionGroup[] = groups || 
    Object.entries(groupedTransactions || {}).map(([key, group]) => ({
      key,
      total_amount_cents: group.total,
      count: group.transactions.length,
      transactions: group.transactions
    }));
  
  // Get all transactions from grouped data for selection logic
  const allTransactions = normalizedGroups.flatMap(group => group.transactions);


  const handleSelectTransaction = (transactionId: string) => {
    setSelectedTransactions(prev => 
      prev.includes(transactionId)
        ? prev.filter(id => id !== transactionId)
        : [...prev, transactionId]
    );
  };

  const handleSelectAll = () => {
    if (selectedTransactions.length === allTransactions.length) {
      setSelectedTransactions([]);
    } else {
      setSelectedTransactions(allTransactions.map(t => t.id));
    }
  };

  const handleBulkDelete = () => {
    if (selectedTransactions.length > 0) {
      onBulkDelete(selectedTransactions);
      setSelectedTransactions([]);
    }
  };

  const handleDeleteConfirm = (transactionId?: string) => {
    if (transactionId) {
      onDelete(transactionId);
    }
    setDeleteConfirm({ isOpen: false });
  };


  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <Card key={i}>
            <div className="p-4 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
                  <div>
                    <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-16"></div>
                  </div>
                </div>
                <div className="h-6 bg-gray-200 rounded w-20"></div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  if (allTransactions.length === 0) {
    return (
      <Card>
        <div className="p-8 text-center">
          <div className="text-6xl mb-4 text-[hsl(var(--text))/0.3]">No Data</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No transactions found</h3>
          <p className="text-gray-500 mb-4">Start by adding your first transaction or adjust your filters.</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Summary */}
      {stats && (
        <Card>
          <div className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(stats.total_income)}
                </div>
                <div className="text-sm text-gray-500">Total Income</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {formatCurrency(stats.total_expenses)}
                </div>
                <div className="text-sm text-gray-500">Total Expenses</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${stats.net_amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(stats.net_amount)}
                </div>
                <div className="text-sm text-gray-500">Net Amount</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {stats.transaction_count}
                </div>
                <div className="text-sm text-gray-500">Transactions</div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Bulk Actions */}
      {allTransactions.length > 0 && (
        <Card>
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedTransactions.length === allTransactions.length}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Select All ({selectedTransactions.length} selected)
                </span>
              </label>
            </div>
            
            {selectedTransactions.length > 0 && (
              <Button
                variant="outline"
                onClick={handleBulkDelete}
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                Delete Selected ({selectedTransactions.length})
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* Grouped Transaction List */}
      <div className="space-y-4">
        {normalizedGroups.map((group) => {
            const isExpanded = expandedGroups.has(group.key);
            
            // Format the group key based on the group type
            const formatGroupKey = (key: string, type: string) => {
              switch (type) {
                case 'date':
                  return formatGroupDate(key);
                case 'category':
                  return `${key}`;
                case 'merchant':
                  return `🏪 ${key}`;
                default:
                  return key;
              }
            };
            
            return (
              <div key={group.key} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                {/* Group Header */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  onClick={() => onToggleGroup(group.key)}
                >
                  <div className="flex items-center space-x-3">
                    <ChevronDown 
                      className={`h-5 w-5 text-gray-500 transition-transform duration-200 ${
                        isExpanded ? 'rotate-0' : '-rotate-90'
                      }`} 
                    />
                    <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
                      {formatGroupKey(group.key, groupType)}
                    </h3>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${
                      group.total_amount_cents >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(group.total_amount_cents)}
                    </p>
                    <p className="text-sm text-gray-500">
                      {group.count} transaction{group.count !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
    
                {/* Collapsible Transaction Items */}
                {isExpanded && (
              <div className="px-4 pb-2 border-t border-[hsl(var(--border))]">
                    <div className="space-y-2 pt-2">
                      {group.transactions.map(transaction => (
                        <TransactionItem
                          key={transaction.id}
                          transaction={transaction}
                          onEdit={onEdit}
                          onDelete={() => setDeleteConfirm({ isOpen: true, transactionId: transaction.id })}
                          showCheckbox={true}
                          isSelected={selectedTransactions.includes(transaction.id)}
                          onSelect={handleSelectTransaction}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false })}
        title="Delete Transaction"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            Are you sure you want to delete this transaction? This action cannot be undone.
          </p>
          
          <div className="flex justify-end space-x-3">
            <Button
              variant="outline"
              onClick={() => setDeleteConfirm({ isOpen: false })}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => handleDeleteConfirm(deleteConfirm.transactionId)}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}