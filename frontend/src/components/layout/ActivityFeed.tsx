import React, { useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { 
  Activity, PlusCircle, Edit3, Trash2, Upload, Wallet, Edit, XCircle, 
  AlertTriangle, Target, Trophy, Flag, Link, RefreshCw, Tag, Zap, 
  MagicWand, CheckCircle, Download, Settings 
} from 'lucide-react';
import { Card } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useRealtimeActivityFeed } from '../../hooks/useActivityFeed';
import { useNewActivitiesCount } from '../../stores/realtimeStore';
import { getActivityIcon, formatActivityDescription, ActivityType } from '../../types/activity';
import type { ActivityEvent } from '../../types/activity';

// Robust icon mapping using explicit imports instead of dynamic loading
const ICON_COMPONENTS: Record<string, React.ComponentType<{ className?: string }>> = {
  'plus-circle': PlusCircle,
  'edit-3': Edit3,
  'trash-2': Trash2,
  'upload': Upload,
  'wallet': Wallet,
  'edit': Edit,
  'x-circle': XCircle,
  'alert-triangle': AlertTriangle,
  'target': Target,
  'trophy': Trophy,
  'flag': Flag,
  'link': Link,
  'refresh-cw': RefreshCw,
  'tag': Tag,
  'zap': Zap,
  'magic-wand': MagicWand,
  'check-circle': CheckCircle,
  'download': Download,
  'settings': Settings,
  'activity': Activity, // fallback icon
};

interface ActivityFeedProps {
  className?: string;
  maxItems?: number;
}

export function ActivityFeed({ className = '', maxItems = 20 }: ActivityFeedProps) {
  const { activities: allActivities, isLoading, error, refetch } = useRealtimeActivityFeed({
    limit: maxItems,
  });
  
  const newActivitiesCount = useNewActivitiesCount();

  // Periodically clear old real-time activities to prevent memory leaks
  useEffect(() => {
    const interval = setInterval(() => {
      if (allActivities.length > 100) {
        // This would require a store action to clean up old activities
        console.log('Cleaning up old real-time activities');
      }
    }, 5 * 60 * 1000); // Every 5 minutes

    return () => clearInterval(interval);
  }, [allActivities.length]);

  if (isLoading && allActivities.length === 0) {
    return (
      <Card className={`p-4 ${className}`}>
        <div className="flex items-center justify-center space-x-2">
          <LoadingSpinner size="sm" />
          <span className="text-sm text-muted-foreground">Loading activities...</span>
        </div>
      </Card>
    );
  }

  if (error && allActivities.length === 0) {
    return (
      <Card className={`p-4 ${className}`}>
        <div className="text-center">
          <div className="text-sm text-destructive mb-2">Failed to load activities</div>
          <button
            onClick={() => refetch()}
            className="text-xs text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`overflow-hidden ${className}`}>
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-foreground">Recent Activity</h3>
          {newActivitiesCount > 0 && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
              {newActivitiesCount} new
            </span>
          )}
        </div>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {allActivities.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No recent activity
          </div>
        ) : (
          <div className="divide-y divide-border">
            {allActivities.map((activity) => (
              <ActivityItem key={activity.id} activity={activity} />
            ))}
          </div>
        )}
      </div>

      {allActivities.length >= maxItems && (
        <div className="p-3 border-t border-border bg-muted/30">
          <button
            onClick={() => refetch()}
            className="w-full text-xs text-primary hover:underline"
          >
            Load more activities
          </button>
        </div>
      )}
    </Card>
  );
}

interface ActivityItemProps {
  activity: ActivityEvent;
}

function ActivityItem({ activity }: ActivityItemProps) {
  const iconName = getActivityIcon(activity.type as ActivityType);
  const IconComponent = ICON_COMPONENTS[iconName] || ICON_COMPONENTS['activity'];
  
  // Format timestamp to relative time
  const timeAgo = formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true });
  
  // Get color based on activity type
  const getActivityColor = (type: string) => {
    const colorMap: Record<string, string> = {
      transaction_created: 'text-green-600',
      transaction_updated: 'text-blue-600',
      transaction_deleted: 'text-red-600',
      budget_created: 'text-purple-600',
      budget_alert: 'text-orange-600',
      goal_achieved: 'text-yellow-600',
      account_synced: 'text-emerald-600',
      rule_applied: 'text-indigo-600',
    };
    return colorMap[type] || 'text-gray-600';
  };

  return (
    <div className={`p-3 hover:bg-muted/50 transition-colors ${activity.isNew ? 'bg-primary/5' : ''}`}>
      <div className="flex items-start space-x-3">
        <div className={`flex-shrink-0 ${getActivityColor(activity.type)}`}>
          <IconComponent className="h-4 w-4" />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground truncate">
              {activity.title}
            </p>
            {activity.isNew && (
              <span className="flex-shrink-0 w-2 h-2 bg-primary rounded-full" />
            )}
          </div>
          
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            {formatActivityDescription(activity)}
          </p>
          
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-muted-foreground">{timeAgo}</span>
            
            {activity.table_name && (
              <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                {activity.table_name}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}