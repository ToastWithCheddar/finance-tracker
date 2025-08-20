import React, { useState, useMemo } from 'react';
import { 
  RefreshCw, 
  Plus, 
  BarChart3, 
  AlertCircle, 
  Activity,
  TrendingUp,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useUnifiedSubscriptions, useUnifiedSubscriptionActions } from '../../hooks/useUnifiedSubscriptions';
import { SubscriptionAnalyticsDashboard } from './SubscriptionAnalyticsDashboard';
import { SubscriptionCostChart } from './SubscriptionCostChart';
import { SubscriptionInsights } from './SubscriptionInsights';
import { UnifiedSubscriptionList } from './UnifiedSubscriptionList';
import type { UnifiedSubscriptionFilter } from '../../types/subscription';

interface SubscriptionManagerProps {
  // Optional props for customization
  defaultView?: 'dashboard' | 'list' | 'insights' | 'charts';
  enableFilters?: boolean;
  enableActions?: boolean;
  showHeader?: boolean;
}

type ViewMode = 'dashboard' | 'list' | 'insights' | 'charts';

/**
 * Main container component for managing subscriptions with multiple view modes.
 * Orchestrates the entire subscription management feature including dashboard,
 * list view, insights, and chart visualizations.
 */
export const SubscriptionManager: React.FC<SubscriptionManagerProps> = ({
  defaultView = 'dashboard',
  enableFilters = true,
  enableActions = true,
  showHeader = true
}) => {
  const [currentView, setCurrentView] = useState<ViewMode>(defaultView);
  const [filters, setFilters] = useState<UnifiedSubscriptionFilter>({});
  const [showInactive, setShowInactive] = useState(false);

  // Enhanced filters that include show inactive toggle
  const enhancedFilters = useMemo(() => ({
    ...filters,
    isActive: showInactive ? undefined : true
  }), [filters, showInactive]);

  // Fetch unified subscription data
  const {
    subscriptions,
    filteredSubscriptions,
    analytics,
    isLoading,
    error,
    refetch,
    plaidData,
    manualData
  } = useUnifiedSubscriptions({ 
    filters: enhancedFilters, 
    enabled: true 
  });

  // Subscription actions
  const actions = useUnifiedSubscriptionActions();

  const handleFiltersChange = (newFilters: UnifiedSubscriptionFilter) => {
    setFilters(newFilters);
  };

  const handleRefresh = () => {
    refetch();
  };

  const handleMute = async (subscription: any, muted: boolean) => {
    try {
      await actions.mute(subscription, muted);
    } catch (error) {
      console.error('Failed to mute subscription:', error);
    }
  };

  const handleLink = async (subscription: any) => {
    // TODO: Implement subscription linking functionality
    // This should open a modal to select which manual rule to link to
    // Placeholder implementation - needs to connect to subscription linking service
  };

  const handleUnlink = async (subscription: any) => {
    try {
      await actions.unlink(subscription);
    } catch (error) {
      console.error('Failed to unlink subscription:', error);
    }
  };

  const handleEdit = async (subscription: any) => {
    // TODO: Implement subscription editing functionality  
    // This should open the edit modal for manual rules
    // Placeholder implementation - needs to connect to subscription editing service
  };

  const handleDelete = async (subscription: any) => {
    try {
      await actions.delete(subscription);
    } catch (error) {
      console.error('Failed to delete subscription:', error);
    }
  };

  // View toggle buttons
  const ViewToggle: React.FC = () => (
    <div className="flex space-x-1 p-1 bg-[hsl(var(--border)/0.15)] rounded-lg w-fit">
      {[
        { id: 'dashboard' as const, label: 'Dashboard', icon: BarChart3 },
        { id: 'list' as const, label: 'List', icon: Activity },
        { id: 'insights' as const, label: 'Insights', icon: AlertCircle },
        { id: 'charts' as const, label: 'Charts', icon: TrendingUp }
      ].map((view) => {
        const Icon = view.icon;
        return (
          <button
            key={view.id}
            onClick={() => setCurrentView(view.id)}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-all
              ${currentView === view.id
                ? 'bg-[hsl(var(--surface))] text-[hsl(var(--text))] shadow-sm'
                : 'text-[hsl(var(--text))/0.7] hover:text-[hsl(var(--text))]'
              }
            `}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{view.label}</span>
          </button>
        );
      })}
    </div>
  );

  // Error state
  if (error) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
          <h3 className="text-lg font-semibold text-[hsl(var(--text))] mb-2">
            Failed to Load Subscriptions
          </h3>
          <p className="text-[hsl(var(--text))] opacity-70 mb-4">
            {error.message || 'An error occurred while loading subscription data.'}
          </p>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <div className="space-y-6">
            <SubscriptionAnalyticsDashboard 
              analytics={analytics} 
              isLoading={isLoading}
            />
            {!isLoading && subscriptions.length > 0 && (
              <>
                <SubscriptionCostChart 
                  subscriptions={filteredSubscriptions} 
                  analytics={analytics}
                />
                <SubscriptionInsights subscriptions={filteredSubscriptions} />
              </>
            )}
          </div>
        );

      case 'list':
        return (
          <UnifiedSubscriptionList
            subscriptions={filteredSubscriptions}
            filters={enhancedFilters}
            onFiltersChange={enableFilters ? handleFiltersChange : undefined}
            onMute={enableActions ? handleMute : undefined}
            onLink={enableActions ? handleLink : undefined}
            onUnlink={enableActions ? handleUnlink : undefined}
            onEdit={enableActions ? handleEdit : undefined}
            onDelete={enableActions ? handleDelete : undefined}
            isLoading={isLoading}
          />
        );

      case 'insights':
        return (
          <div className="space-y-6">
            {isLoading ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <LoadingSpinner />
                  <p className="mt-2 text-[hsl(var(--text))] opacity-70">
                    Analyzing subscriptions...
                  </p>
                </CardContent>
              </Card>
            ) : (
              <SubscriptionInsights subscriptions={filteredSubscriptions} />
            )}
          </div>
        );

      case 'charts':
        return (
          <div className="space-y-6">
            {isLoading ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <LoadingSpinner />
                  <p className="mt-2 text-[hsl(var(--text))] opacity-70">
                    Loading charts...
                  </p>
                </CardContent>
              </Card>
            ) : (
              <SubscriptionCostChart 
                subscriptions={filteredSubscriptions} 
                analytics={analytics}
              />
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      {showHeader && (
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-[hsl(var(--text))]">
              Subscription Management
            </h2>
            <p className="text-[hsl(var(--text))] opacity-70 mt-1">
              Unified view of all your subscriptions and recurring payments
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {/* Show inactive toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowInactive(!showInactive)}
              className={showInactive ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-300' : ''}
            >
              {showInactive ? <Eye className="h-4 w-4 mr-2" /> : <EyeOff className="h-4 w-4 mr-2" />}
              {showInactive ? 'Hide Inactive' : 'Show Inactive'}
            </Button>
            
            {/* Refresh button */}
            <Button
              onClick={handleRefresh}
              disabled={isLoading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              {isLoading ? 'Loading...' : 'Refresh'}
            </Button>
            
            {/* Add new subscription button */}
            {enableActions && (
              <Button
                onClick={() => {
                  // TODO: Implement add new subscription functionality
                  // This should open a modal for creating a new subscription
                }}
                className="bg-blue-600 hover:bg-blue-700"
                size="sm"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Rule
              </Button>
            )}
          </div>
        </div>
      )}

      {/* View Toggle */}
      <div className="flex items-center justify-between">
        <ViewToggle />
        
        {/* Quick Stats */}
        {!isLoading && (
          <div className="flex items-center space-x-6 text-sm text-[hsl(var(--text))] opacity-70">
            <span>{analytics.activeSubscriptionCount} active</span>
            <span>{analytics.subscriptionCount} total</span>
            <span className="font-semibold text-[hsl(var(--text))]">
              ${(analytics.totalMonthlyCents / 100).toFixed(0)}/month
            </span>
          </div>
        )}
      </div>

      {/* Main Content */}
      {renderCurrentView()}

      {/* Loading Overlay for Actions */}
      {actions.isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <LoadingSpinner />
                <span className="text-[hsl(var(--text))]">
                  Processing subscription action...
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};