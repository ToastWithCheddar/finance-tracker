import React, { useState, useMemo } from 'react';
import { 
  Search,
  Filter,
  MoreVertical,
  Calendar,
  DollarSign,
  Building,
  Tag,
  Eye,
  EyeOff,
  Link,
  Unlink,
  Edit,
  Trash2,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { formatCurrency } from '../../utils/currency';
import type { UnifiedSubscription, UnifiedSubscriptionFilter } from '../../types/subscription';

interface UnifiedSubscriptionListProps {
  subscriptions: UnifiedSubscription[];
  filters?: UnifiedSubscriptionFilter;
  onFiltersChange?: (filters: UnifiedSubscriptionFilter) => void;
  onMute?: (subscription: UnifiedSubscription, muted: boolean) => void;
  onLink?: (plaidSubscription: UnifiedSubscription, manualSubscription: UnifiedSubscription) => void;
  onUnlink?: (subscription: UnifiedSubscription) => void;
  onEdit?: (subscription: UnifiedSubscription) => void;
  onDelete?: (subscription: UnifiedSubscription) => void;
  isLoading?: boolean;
}

interface SubscriptionCardProps {
  subscription: UnifiedSubscription;
  onMute?: (subscription: UnifiedSubscription, muted: boolean) => void;
  onLink?: (subscription: UnifiedSubscription) => void;
  onUnlink?: (subscription: UnifiedSubscription) => void;
  onEdit?: (subscription: UnifiedSubscription) => void;
  onDelete?: (subscription: UnifiedSubscription) => void;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscription,
  onMute,
  onLink,
  onUnlink,
  onEdit,
  onDelete
}) => {
  const [showActions, setShowActions] = useState(false);

  const getStatusBadge = () => {
    if (subscription.isMuted) {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
          Muted
        </span>
      );
    }
    
    if (!subscription.isActive) {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400">
          Inactive
        </span>
      );
    }

    if (subscription.isLinked) {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400">
          Linked
        </span>
      );
    }

    return (
      <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400">
        Active
      </span>
    );
  };

  const getSourceBadge = () => {
    const isPlaid = subscription.source === 'plaid';
    return (
      <span className={`px-2 py-1 text-xs rounded-full ${
        isPlaid 
          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
          : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
      }`}>
        {isPlaid ? 'Plaid' : 'Manual'}
      </span>
    );
  };

  const getConfidenceIndicator = () => {
    const confidence = subscription.insights?.confidenceScore;
    if (!confidence) return null;

    if (confidence >= 90) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    } else if (confidence >= 70) {
      return <Clock className="h-4 w-4 text-yellow-500" />;
    } else {
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const formatNextDueDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      return 'Overdue';
    } else if (diffDays === 0) {
      return 'Due today';
    } else if (diffDays === 1) {
      return 'Due tomorrow';
    } else if (diffDays <= 7) {
      return `Due in ${diffDays} days`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <Card className={`transition-all duration-200 hover:shadow-md ${
      subscription.isMuted ? 'opacity-60' : ''
    }`}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <h3 className="text-lg font-semibold text-[hsl(var(--text))] truncate">
                    {subscription.name}
                  </h3>
                  {getConfidenceIndicator()}
                </div>
                <p className="text-sm text-[hsl(var(--text))] opacity-70 truncate">
                  {subscription.description}
                </p>
              </div>
              <div className="flex items-center space-x-2 ml-4">
                {getStatusBadge()}
                {getSourceBadge()}
              </div>
            </div>

            {/* Amount and Frequency */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-1 text-lg font-bold text-[hsl(var(--text))]">
                  <DollarSign className="h-4 w-4" />
                  <span>{formatCurrency(subscription.monthlyEstimatedCents / 100)}</span>
                  <span className="text-sm font-normal opacity-60">/month</span>
                </div>
                <span className="text-sm text-[hsl(var(--text))] opacity-60 capitalize">
                  {subscription.frequency.toLowerCase()}
                </span>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-[hsl(var(--text))]">
                  {formatCurrency(subscription.amountDollars)}
                </p>
                <p className="text-xs text-[hsl(var(--text))] opacity-60">
                  per payment
                </p>
              </div>
            </div>

            {/* Metadata */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                <span className="text-[hsl(var(--text))] opacity-80">
                  {formatNextDueDate(subscription.nextDueDate)}
                </span>
              </div>
              
              {subscription.categoryName && (
                <div className="flex items-center space-x-2">
                  <Tag className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                  <span className="text-[hsl(var(--text))] opacity-80 truncate">
                    {subscription.categoryName}
                  </span>
                </div>
              )}
              
              {subscription.merchantName && (
                <div className="flex items-center space-x-2">
                  <Building className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                  <span className="text-[hsl(var(--text))] opacity-80 truncate">
                    {subscription.merchantName}
                  </span>
                </div>
              )}
              
              {subscription.lastTransactionDate && (
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                  <span className="text-[hsl(var(--text))] opacity-80">
                    Last: {new Date(subscription.lastTransactionDate).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>

            {/* Insights */}
            {subscription.insights && (
              <div className="mt-3 pt-3 border-t border-[hsl(var(--border))]">
                {subscription.insights.isLowUsage && (
                  <div className="flex items-center space-x-2 text-sm text-orange-600 dark:text-orange-400">
                    <AlertCircle className="h-4 w-4" />
                    <span>Low usage detected</span>
                  </div>
                )}
                {subscription.insights.priceChangeDetected && (
                  <div className="flex items-center space-x-2 text-sm text-red-600 dark:text-red-400">
                    <TrendingUp className="h-4 w-4" />
                    <span>Price increase detected</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Actions Menu */}
          <div className="relative ml-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowActions(!showActions)}
              className="h-8 w-8 p-0"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
            
            {showActions && (
              <div className="absolute right-0 top-8 z-10 w-48 bg-white dark:bg-gray-800 border border-[hsl(var(--border))] rounded-lg shadow-lg py-1">
                {subscription.source === 'plaid' && onMute && (
                  <button
                    onClick={() => {
                      onMute(subscription, !subscription.isMuted);
                      setShowActions(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    {subscription.isMuted ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                    <span>{subscription.isMuted ? 'Unmute' : 'Mute'}</span>
                  </button>
                )}
                
                {subscription.source === 'plaid' && !subscription.isLinked && onLink && (
                  <button
                    onClick={() => {
                      onLink(subscription);
                      setShowActions(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <Link className="h-4 w-4" />
                    <span>Link to Rule</span>
                  </button>
                )}
                
                {subscription.source === 'plaid' && subscription.isLinked && onUnlink && (
                  <button
                    onClick={() => {
                      onUnlink(subscription);
                      setShowActions(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <Unlink className="h-4 w-4" />
                    <span>Unlink</span>
                  </button>
                )}
                
                {subscription.source === 'manual' && onEdit && (
                  <button
                    onClick={() => {
                      onEdit(subscription);
                      setShowActions(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <Edit className="h-4 w-4" />
                    <span>Edit Rule</span>
                  </button>
                )}
                
                {subscription.source === 'manual' && onDelete && (
                  <button
                    onClick={() => {
                      onDelete(subscription);
                      setShowActions(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2 text-red-600 dark:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                    <span>Delete Rule</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const FilterBar: React.FC<{
  filters?: UnifiedSubscriptionFilter;
  onFiltersChange?: (filters: UnifiedSubscriptionFilter) => void;
  subscriptionCount: number;
}> = ({ filters, onFiltersChange, subscriptionCount }) => {
  const [searchTerm, setSearchTerm] = useState(filters?.search || '');
  const [showFilters, setShowFilters] = useState(false);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    onFiltersChange?.({ ...filters, search: value || undefined });
  };

  const handleFilterChange = (key: keyof UnifiedSubscriptionFilter, value: any) => {
    onFiltersChange?.({ ...filters, [key]: value });
  };

  const clearFilters = () => {
    setSearchTerm('');
    onFiltersChange?.({});
  };

  const hasActiveFilters = filters && Object.keys(filters).some(key => 
    filters[key as keyof UnifiedSubscriptionFilter] !== undefined
  );

  return (
    <div className="space-y-4">
      {/* Search and Quick Filters */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search subscriptions..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--surface))] text-[hsl(var(--text))] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className={hasActiveFilters ? 'border-blue-500 text-blue-600' : ''}
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
          {hasActiveFilters && (
            <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-500 text-white rounded-full">
              !
            </span>
          )}
        </Button>

        {hasActiveFilters && (
          <Button variant="ghost" onClick={clearFilters} size="sm">
            Clear
          </Button>
        )}
      </div>

      {/* Extended Filters */}
      {showFilters && (
        <Card>
          <CardContent className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--text))] mb-1">
                  Source
                </label>
                <select
                  value={filters?.source || 'all'}
                  onChange={(e) => handleFilterChange('source', e.target.value === 'all' ? undefined : e.target.value)}
                  className="w-full px-3 py-2 border border-[hsl(var(--border))] rounded bg-[hsl(var(--surface))] text-[hsl(var(--text))]"
                >
                  <option value="all">All Sources</option>
                  <option value="plaid">Plaid Detected</option>
                  <option value="manual">Manual Rules</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[hsl(var(--text))] mb-1">
                  Status
                </label>
                <select
                  value={filters?.isActive?.toString() || 'all'}
                  onChange={(e) => handleFilterChange('isActive', e.target.value === 'all' ? undefined : e.target.value === 'true')}
                  className="w-full px-3 py-2 border border-[hsl(var(--border))] rounded bg-[hsl(var(--surface))] text-[hsl(var(--text))]"
                >
                  <option value="all">All Statuses</option>
                  <option value="true">Active</option>
                  <option value="false">Inactive</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[hsl(var(--text))] mb-1">
                  Frequency
                </label>
                <select
                  value={filters?.frequency || 'all'}
                  onChange={(e) => handleFilterChange('frequency', e.target.value === 'all' ? undefined : e.target.value)}
                  className="w-full px-3 py-2 border border-[hsl(var(--border))] rounded bg-[hsl(var(--surface))] text-[hsl(var(--text))]"
                >
                  <option value="all">All Frequencies</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="BIWEEKLY">Biweekly</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="QUARTERLY">Quarterly</option>
                  <option value="ANNUALLY">Annually</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[hsl(var(--text))] mb-1">
                  Amount Range
                </label>
                <div className="flex space-x-2">
                  <input
                    type="number"
                    placeholder="Min"
                    value={filters?.minAmountCents ? (filters.minAmountCents / 100).toString() : ''}
                    onChange={(e) => handleFilterChange('minAmountCents', e.target.value ? parseInt(e.target.value) * 100 : undefined)}
                    className="w-full px-2 py-2 border border-[hsl(var(--border))] rounded bg-[hsl(var(--surface))] text-[hsl(var(--text))] text-sm"
                  />
                  <input
                    type="number"
                    placeholder="Max"
                    value={filters?.maxAmountCents ? (filters.maxAmountCents / 100).toString() : ''}
                    onChange={(e) => handleFilterChange('maxAmountCents', e.target.value ? parseInt(e.target.value) * 100 : undefined)}
                    className="w-full px-2 py-2 border border-[hsl(var(--border))] rounded bg-[hsl(var(--surface))] text-[hsl(var(--text))] text-sm"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--text))] opacity-70">
          Showing {subscriptionCount} subscription{subscriptionCount !== 1 ? 's' : ''}
          {hasActiveFilters ? ' (filtered)' : ''}
        </p>
      </div>
    </div>
  );
};

/**
 * Comprehensive list component for displaying unified subscriptions with filtering,
 * search, and action capabilities. Handles both Plaid-detected and manual
 * subscriptions through the unified data model.
 */
export const UnifiedSubscriptionList: React.FC<UnifiedSubscriptionListProps> = ({
  subscriptions,
  filters,
  onFiltersChange,
  onMute,
  onLink,
  onUnlink,
  onEdit,
  onDelete,
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="flex items-center justify-center">
            <LoadingSpinner />
            <span className="ml-2 text-[hsl(var(--text))] opacity-70">
              Loading subscriptions...
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (subscriptions.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Zap className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-2">
            No Subscriptions Found
          </h3>
          <p className="text-[hsl(var(--text))] opacity-70">
            Connect your accounts or add manual rules to get started with subscription tracking.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <FilterBar
        filters={filters}
        onFiltersChange={onFiltersChange}
        subscriptionCount={subscriptions.length}
      />
      
      <div className="space-y-4">
        {subscriptions.map(subscription => (
          <SubscriptionCard
            key={subscription.id}
            subscription={subscription}
            onMute={onMute}
            onLink={onLink}
            onUnlink={onUnlink}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
};