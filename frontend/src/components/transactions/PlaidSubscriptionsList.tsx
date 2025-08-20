import React, { useState } from 'react';
import { 
  VolumeX, 
  Volume2, 
  Link, 
  Unlink, 
  Calendar, 
  DollarSign, 
  Building, 
  ChevronDown,
  ChevronUp,
  Filter,
  Search,
  MoreVertical,
  Check,
  X
} from 'lucide-react';
import { Button } from '../ui/Button';
import { formatCurrency } from '../../utils/currency';
import { usePlaidRecurringActions } from '../../hooks/usePlaidRecurring';
import type { 
  PlaidRecurringTransaction, 
  PlaidRecurringFilter 
} from '../../types/plaidRecurring';

interface PlaidSubscriptionsListProps {
  transactions: PlaidRecurringTransaction[];
  onFiltersChange: (filters: PlaidRecurringFilter) => void;
  filters: PlaidRecurringFilter;
}

interface PlaidSubscriptionCardProps {
  transaction: PlaidRecurringTransaction;
  onMute: (id: string, muted: boolean) => void;
  onLink: (id: string) => void;
  onUnlink: (id: string) => void;
  isLoading: boolean;
}

const PlaidSubscriptionCard: React.FC<PlaidSubscriptionCardProps> = ({
  transaction,
  onMute,
  onLink,
  onUnlink,
  isLoading
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'MATURE':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100';
      case 'EARLY_DETECTION':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100';
      case 'INACCURATE':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100';
      case 'TERMINATED':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100';
    }
  };

  const getFrequencyColor = (frequency: string) => {
    switch (frequency) {
      case 'MONTHLY':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100';
      case 'WEEKLY':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100';
      case 'ANNUALLY':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100';
    }
  };

  return (
    <div className={`
      bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg p-4 
      transition-all duration-200 hover:shadow-md
      ${transaction.is_muted ? 'opacity-60' : ''}
    `}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-12 h-12 bg-[hsl(var(--brand))] text-white rounded-lg flex items-center justify-center">
              <Building className="h-6 w-6" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-[hsl(var(--text))] truncate">
              {transaction.merchant_name || transaction.description}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(transaction.plaid_status)}`}>
                {transaction.plaid_status.replace('_', ' ')}
              </span>
              <span className={`px-2 py-1 text-xs font-medium rounded ${getFrequencyColor(transaction.plaid_frequency)}`}>
                {transaction.plaid_frequency}
              </span>
              {transaction.is_muted && (
                <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100">
                  MUTED
                </span>
              )}
              {transaction.is_linked_to_rule && (
                <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100">
                  LINKED
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div className="text-right">
            <p className="text-lg font-bold text-[hsl(var(--text))]">
              {formatCurrency(transaction.monthly_estimated_amount_cents / 100)}
            </p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">per month</p>
          </div>
          
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowActions(!showActions)}
              disabled={isLoading}
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
            
            {showActions && (
              <div className="absolute right-0 mt-2 w-48 bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg shadow-lg z-10">
                <div className="p-1">
                  <button
                    onClick={() => {
                      onMute(transaction.plaid_recurring_transaction_id, !transaction.is_muted);
                      setShowActions(false);
                    }}
                    disabled={isLoading}
                    className="flex items-center w-full px-3 py-2 text-sm text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] rounded disabled:opacity-50"
                  >
                    {transaction.is_muted ? (
                      <>
                        <Volume2 className="h-4 w-4 mr-2" />
                        Unmute notifications
                      </>
                    ) : (
                      <>
                        <VolumeX className="h-4 w-4 mr-2" />
                        Mute notifications
                      </>
                    )}
                  </button>
                  
                  {transaction.is_linked_to_rule ? (
                    <button
                      onClick={() => {
                        onUnlink(transaction.plaid_recurring_transaction_id);
                        setShowActions(false);
                      }}
                      disabled={isLoading}
                      className="flex items-center w-full px-3 py-2 text-sm text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] rounded disabled:opacity-50"
                    >
                      <Unlink className="h-4 w-4 mr-2" />
                      Unlink from rule
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        onLink(transaction.plaid_recurring_transaction_id);
                        setShowActions(false);
                      }}
                      disabled={isLoading}
                      className="flex items-center w-full px-3 py-2 text-sm text-[hsl(var(--text))] hover:bg-[hsl(var(--border)/0.25)] rounded disabled:opacity-50"
                    >
                      <Link className="h-4 w-4 mr-2" />
                      Link to rule
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Details */}
      {showDetails && (
        <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-[hsl(var(--text))] mb-2">Transaction Details</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">Last Amount:</span>
                  <span className="text-[hsl(var(--text))]">{formatCurrency(transaction.last_amount_cents / 100)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">Last Date:</span>
                  <span className="text-[hsl(var(--text))]">
                    {new Date(transaction.last_date).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">Currency:</span>
                  <span className="text-[hsl(var(--text))]">{transaction.currency}</span>
                </div>
                {transaction.plaid_category && (
                  <div className="flex justify-between">
                    <span className="text-[hsl(var(--text))] opacity-70">Category:</span>
                    <span className="text-[hsl(var(--text))]">{transaction.plaid_category.join(' > ')}</span>
                  </div>
                )}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-[hsl(var(--text))] mb-2">Detection Info</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">First Detected:</span>
                  <span className="text-[hsl(var(--text))]">
                    {new Date(transaction.first_detected_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">Sync Count:</span>
                  <span className="text-[hsl(var(--text))]">{transaction.sync_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">Mature:</span>
                  <span className="text-[hsl(var(--text))]">
                    {transaction.is_mature ? (
                      <Check className="h-4 w-4 text-green-500 inline" />
                    ) : (
                      <X className="h-4 w-4 text-red-500 inline" />
                    )}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[hsl(var(--text))] opacity-70">Last Sync:</span>
                  <span className="text-[hsl(var(--text))]">
                    {new Date(transaction.last_sync_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const PlaidSubscriptionsList: React.FC<PlaidSubscriptionsListProps> = ({
  transactions,
  onFiltersChange,
  filters
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  
  const actions = usePlaidRecurringActions();

  // Filter transactions based on search and filters
  const filteredTransactions = transactions.filter(transaction => {
    const matchesSearch = !searchTerm || 
      (transaction.merchant_name?.toLowerCase().includes(searchTerm.toLowerCase())) ||
      transaction.description.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesSearch;
  });

  const handleMute = (id: string, muted: boolean) => {
    actions.mute.mutate({ plaidRecurringId: id, muted });
  };

  /**
   * Links a Plaid-detected subscription to a manual categorization rule
   * @param id - ID of the Plaid subscription to link
   * 
   * TODO: Implement subscription linking modal
   * Implementation should:
   * 1. Open a modal component (e.g., SubscriptionLinkModal)
   * 2. Show subscription details (merchant, amount, frequency)
   * 3. Provide options to:
   *    a) Link to existing rule:
   *       - Display searchable list of compatible manual rules
   *       - Show rule preview with conditions and target category
   *       - Validate rule compatibility with subscription pattern
   *    b) Create new rule:
   *       - Pre-populate rule form with subscription data
   *       - Set merchant name, amount range, frequency conditions
   *       - Allow user to select target category
   * 4. Call link mutation with selected rule ID or new rule data
   * 5. Update subscription status and refresh list on success
   * 6. Show confirmation toast with linked rule details
   */
  const handleLink = (id: string) => {
    console.log('Link subscription to rule:', id);
  };

  const handleUnlink = (id: string) => {
    actions.unlink.mutate(id);
  };

  const handleBulkMute = (muted: boolean) => {
    if (selectedItems.length > 0) {
      actions.bulkMute.mutate({
        plaid_recurring_ids: selectedItems,
        muted
      });
      setSelectedItems([]);
    }
  };

  const handleSelectAll = () => {
    if (selectedItems.length === filteredTransactions.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredTransactions.map(t => t.plaid_recurring_transaction_id));
    }
  };

  const handleSelectItem = (id: string) => {
    setSelectedItems(prev => 
      prev.includes(id) 
        ? prev.filter(item => item !== id)
        : [...prev, id]
    );
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[hsl(var(--text))] opacity-50" />
          <input
            type="text"
            placeholder="Search subscriptions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--surface))] text-[hsl(var(--text))] placeholder-[hsl(var(--text))/0.5] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-transparent"
          />
        </div>
        
        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center"
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
        </Button>
      </div>

      {/* Bulk Actions */}
      {selectedItems.length > 0 && (
        <div className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[hsl(var(--text))]">
              {selectedItems.length} subscription{selectedItems.length !== 1 ? 's' : ''} selected
            </span>
            <div className="flex space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkMute(true)}
                disabled={actions.isLoading}
              >
                <VolumeX className="h-4 w-4 mr-2" />
                Mute Selected
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkMute(false)}
                disabled={actions.isLoading}
              >
                <Volume2 className="h-4 w-4 mr-2" />
                Unmute Selected
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedItems([])}
              >
                Clear
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Select All Checkbox */}
      {filteredTransactions.length > 0 && (
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={selectedItems.length === filteredTransactions.length}
            onChange={handleSelectAll}
            className="rounded"
          />
          <span className="text-sm text-[hsl(var(--text))]">
            Select all ({filteredTransactions.length})
          </span>
        </div>
      )}

      {/* Subscription Cards */}
      <div className="space-y-4">
        {filteredTransactions.map((transaction) => (
          <div key={transaction.plaid_recurring_transaction_id} className="flex items-start space-x-3">
            <input
              type="checkbox"
              checked={selectedItems.includes(transaction.plaid_recurring_transaction_id)}
              onChange={() => handleSelectItem(transaction.plaid_recurring_transaction_id)}
              className="mt-6 rounded"
            />
            <div className="flex-1">
              <PlaidSubscriptionCard
                transaction={transaction}
                onMute={handleMute}
                onLink={handleLink}
                onUnlink={handleUnlink}
                isLoading={actions.isLoading}
              />
            </div>
          </div>
        ))}
      </div>

      {filteredTransactions.length === 0 && searchTerm && (
        <div className="text-center py-8">
          <Search className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
          <p className="text-[hsl(var(--text))] opacity-80">No subscriptions match your search.</p>
          <p className="text-sm text-[hsl(var(--text))] opacity-70">
            Try adjusting your search terms or clearing the search.
          </p>
        </div>
      )}
    </div>
  );
};