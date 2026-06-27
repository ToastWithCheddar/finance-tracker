import { useState, type CSSProperties } from 'react';
import { FixedSizeList as VirtualList } from 'react-window';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { TransactionItem } from './TransactionItem';
import { formatCurrency } from '../../utils';
import type { Transaction, TransactionStats } from '../../types/transaction';

// FE-PERF-003: virtualize the list when it grows long enough to matter.
// Below VIRTUALIZE_THRESHOLD we render the plain map so component-level
// vitest fixtures and Playwright snapshots stay deterministic; above it,
// react-window's FixedSizeList scrolls smoothly past 1000+ rows.
const VIRTUALIZE_THRESHOLD = 50;
const ROW_HEIGHT = 88; // measured TransactionItem height incl. spacing
const VIRTUAL_LIST_MAX_HEIGHT = 600;


interface TransactionListProps {
  /**
   * Flat transaction data array.
   * All transactions displayed as individual cards.
   */
  transactions: Transaction[];
  stats?: TransactionStats;
  isLoading?: boolean;
  onEdit: (transaction: Transaction) => void;
  onDelete: (transactionId: string) => void;
  onBulkDelete: (transactionIds: string[]) => void;
}

export function TransactionList({ 
  transactions,
  stats,
  isLoading = false,
  onEdit, 
  onDelete,
  onBulkDelete
}: TransactionListProps) {
  const [selectedTransactions, setSelectedTransactions] = useState<string[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; transactionId?: string }>({
    isOpen: false
  });


  const handleSelectTransaction = (transactionId: string) => {
    setSelectedTransactions(prev => 
      prev.includes(transactionId)
        ? prev.filter(id => id !== transactionId)
        : [...prev, transactionId]
    );
  };

  const handleSelectAll = () => {
    if (selectedTransactions.length === transactions.length) {
      setSelectedTransactions([]);
    } else {
      setSelectedTransactions(transactions.map(t => t.id));
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

  if (transactions.length === 0) {
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
                  {stats.total_count}
                </div>
                <div className="text-sm text-gray-500">Transactions</div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Bulk Actions */}
      {transactions.length > 0 && (
        <Card>
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedTransactions.length === transactions.length}
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

      {/* Flat Transaction List — virtualized above VIRTUALIZE_THRESHOLD. */}
      {transactions.length >= VIRTUALIZE_THRESHOLD ? (
        <VirtualList
          height={Math.min(VIRTUAL_LIST_MAX_HEIGHT, transactions.length * ROW_HEIGHT)}
          itemCount={transactions.length}
          itemSize={ROW_HEIGHT}
          width="100%"
        >
          {({ index, style }: { index: number; style: CSSProperties }) => {
            const transaction = transactions[index];
            return (
              <div style={style} className="pb-3">
                <TransactionItem
                  transaction={transaction}
                  onEdit={onEdit}
                  onDelete={() => setDeleteConfirm({ isOpen: true, transactionId: transaction.id })}
                  showCheckbox={true}
                  isSelected={selectedTransactions.includes(transaction.id)}
                  onSelect={handleSelectTransaction}
                />
              </div>
            );
          }}
        </VirtualList>
      ) : (
        <div className="space-y-3">
          {transactions.map((transaction) => (
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
      )}

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