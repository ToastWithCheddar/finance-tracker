import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui';
import type { Transaction, TransactionStats } from '../../types/transactions';

interface TransactionListProps {
  transactions: Transaction[];
  stats?: TransactionStats;
  isLoading?: boolean;
  onEdit: (transaction: Transaction) => void;
  onDelete: (transactionId: number) => void;
  onBulkDelete: (transactionIds: number[]) => void;
}

export function TransactionList({ 
  transactions, 
  stats,
  isLoading = false,
  onEdit, 
  onDelete,
  onBulkDelete 
}: TransactionListProps) {
  const [selectedTransactions, setSelectedTransactions] = useState<number[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; transactionId?: number }>({
    isOpen: false
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleSelectTransaction = (transactionId: number) => {
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

  const handleDeleteConfirm = (transactionId?: number) => {
    if (transactionId) {
      onDelete(transactionId);
    }
    setDeleteConfirm({ isOpen: false });
  };

  const getTransactionIcon = (type: string, category?: string) => {
    if (type === 'income') return '💰';
    
    // Expense icons by category
    const categoryIcons: Record<string, string> = {
      'Food & Dining': '🍽️',
      'Transportation': '🚗',
      'Shopping': '🛍️',
      'Entertainment': '🎬',
      'Bills & Utilities': '📄',
      'Healthcare': '🏥',
      'Education': '📚',
      'Travel': '✈️',
      'Groceries': '🛒',
      'Gas': '⛽',
      'Rent': '🏠',
      'Insurance': '🛡️',
      'Salary': '💼',
      'Freelance': '💻',
      'Investment': '📈',
      'Gift': '🎁',
      'Refund': '↩️',
    };
    
    return categoryIcons[category || ''] || '💸';
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
          <div className="text-6xl mb-4">📊</div>
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

      {/* Transaction List */}
      <div className="space-y-2">
        {transactions.map((transaction) => (
          <Card key={transaction.id} className="hover:shadow-md transition-shadow">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedTransactions.includes(transaction.id)}
                    onChange={() => handleSelectTransaction(transaction.id)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  
                  <div className="text-2xl">
                    {getTransactionIcon(transaction.transaction_type, transaction.category)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-gray-900 truncate">
                        {transaction.category}
                      </h4>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        transaction.transaction_type === 'income' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {transaction.transaction_type}
                      </span>
                    </div>
                    
                    {transaction.description && (
                      <p className="text-sm text-gray-500 truncate mt-1">
                        {transaction.description}
                      </p>
                    )}
                    
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(transaction.transaction_date)}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className={`text-lg font-semibold ${
                    transaction.transaction_type === 'income' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {transaction.transaction_type === 'income' ? '+' : '-'}
                    {formatCurrency(Math.abs(transaction.amount))}
                  </div>
                  
                  <div className="flex space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(transaction)}
                      className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                    >
                      ✏️
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirm({ isOpen: true, transactionId: transaction.id })}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      🗑️
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
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