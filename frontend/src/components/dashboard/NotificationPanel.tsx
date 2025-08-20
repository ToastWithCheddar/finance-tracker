// frontend/src/components/dashboard/NotificationPanel.tsx
import React, { useState, useMemo } from 'react';
import { 
  Bell, 
  BellOff, 
  X, 
  CheckCircle, 
  AlertTriangle, 
  Info, 
  AlertCircle,
  Target,
  PiggyBank,
  Sparkles,
  ExternalLink,
  Search,
  Filter,
  ChevronDown
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import type { RealtimeNotification } from '../../stores/realtimeStore';
import { useRealtimeStore } from '../../stores/realtimeStore';
import { formatRelativeTime } from '../../utils';

interface NotificationPanelProps {
  notifications: RealtimeNotification[];
  unreadCount: number;
}

export const NotificationPanel: React.FC<NotificationPanelProps> = ({
  notifications,
  unreadCount
}) => {
  const { 
    markNotificationRead, 
    markAllNotificationsRead, 
    dismissNotification
  } = useRealtimeStore();
  
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Define available notification types for filtering
  const notificationTypes = [
    { value: 'all', label: 'All Types' },
    { value: 'budget_alert', label: 'Budget Alert' },
    { value: 'goal_milestone', label: 'Goal Milestone' },
    { value: 'goal_achieved', label: 'Goal Achieved' },
    { value: 'success', label: 'Success' },
    { value: 'error', label: 'Error' },
    { value: 'warning', label: 'Warning' },
    { value: 'ai_insight_generated', label: 'AI Insight' },
    { value: 'spending_pattern_detected', label: 'Spending Pattern' },
    { value: 'goal_progress_update', label: 'Goal Progress' },
  ];

  // Helper function to group notifications by date
  const groupNotificationsByDate = (notifications: RealtimeNotification[]) => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const groups: { [key: string]: RealtimeNotification[] } = {
      'Today': [],
      'Yesterday': [],
      'Older': []
    };

    notifications.forEach(notification => {
      const notificationDate = new Date(notification.created_at);
      const isToday = notificationDate.toDateString() === today.toDateString();
      const isYesterday = notificationDate.toDateString() === yesterday.toDateString();

      if (isToday) {
        groups['Today'].push(notification);
      } else if (isYesterday) {
        groups['Yesterday'].push(notification);
      } else {
        groups['Older'].push(notification);
      }
    });

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) {
        delete groups[key];
      }
    });

    return groups;
  };

  // Enhanced filtering logic with memoization
  const filteredNotifications = useMemo(() => {
    return notifications.filter(notification => {
      // Filter by read status
      const matchesReadFilter = filter === 'all' || !notification.read;
      
      // Filter by type
      const matchesTypeFilter = typeFilter === 'all' || notification.type === typeFilter;
      
      // Filter by search query (case-insensitive search in title and message)
      const matchesSearchQuery = !searchQuery || 
        notification.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        notification.message.toLowerCase().includes(searchQuery.toLowerCase());
      
      return matchesReadFilter && matchesTypeFilter && matchesSearchQuery;
    });
  }, [notifications, filter, typeFilter, searchQuery]);

  // Group filtered notifications by date
  const groupedNotifications = useMemo(() => {
    return groupNotificationsByDate(filteredNotifications);
  }, [filteredNotifications]);

  const handleNotificationClick = (notification: RealtimeNotification) => {
    if (!notification.read) {
      markNotificationRead(notification.id);
    }
    
    // Handle action URL if present
    if (notification.action_url) {
      window.open(notification.action_url, '_blank');
    }
  };

  const handleDismiss = (e: React.MouseEvent, notificationId: string) => {
    e.stopPropagation();
    dismissNotification(notificationId);
  };

  const getNotificationIcon = (type: string, priority: string) => {
    const iconClass = `h-5 w-5 ${
      priority === 'critical' ? 'text-red-500' :
      priority === 'high' ? 'text-orange-500' :
      priority === 'medium' ? 'text-blue-500' :
      'text-gray-500'
    }`;

    switch (type) {
      case 'success':
      case 'goal_achieved':
        return <CheckCircle className={iconClass} />;
      case 'error':
      case 'budget_exceeded':
        return <AlertCircle className={iconClass} />;
      case 'warning':
      case 'budget_alert':
        return <AlertTriangle className={iconClass} />;
      case 'budget_threshold_reached':
        return <PiggyBank className={iconClass} />;
      case 'ai_insight_generated':
      case 'spending_pattern_detected':
        return <Sparkles className={iconClass} />;
      case 'goal_progress_update':
        return <Target className={iconClass} />;
      default:
        return <Info className={iconClass} />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'border-l-red-500 bg-red-50';
      case 'high':
        return 'border-l-orange-500 bg-orange-50';
      case 'medium':
        return 'border-l-blue-500 bg-blue-50';
      case 'low':
      default:
        return 'border-l-gray-500 bg-gray-50';
    }
  };

  if (notifications.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Bell className="h-5 w-5 mr-2" />
            Notifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <BellOff className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              All caught up!
            </h3>
            <p className="text-gray-600">
              You have no new notifications.
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
            <Bell className="h-5 w-5 mr-2" />
            <span>Notifications</span>
            {unreadCount > 0 && (
              <span className="ml-2 px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                {unreadCount}
              </span>
            )}
            {filteredNotifications.length !== notifications.length && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                {filteredNotifications.length} filtered
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Advanced Filters Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="flex items-center gap-1"
            >
              <Filter className="h-4 w-4" />
              <ChevronDown className={`h-3 w-3 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`} />
            </Button>
            
            {/* Filter Toggle */}
            <div className="flex items-center border rounded-md overflow-hidden">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 text-xs ${
                  filter === 'all' 
                    ? 'bg-blue-100 text-blue-800' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilter('unread')}
                className={`px-3 py-1 text-xs ${
                  filter === 'unread' 
                    ? 'bg-blue-100 text-blue-800' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                Unread ({unreadCount})
              </button>
            </div>
            
            {/* Mark All Read */}
            {unreadCount > 0 && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={markAllNotificationsRead}
              >
                Mark All Read
              </Button>
            )}
          </div>
        </CardTitle>

        {/* Advanced Filters Section */}
        {showAdvancedFilters && (
          <div className="mt-4 space-y-3 pt-3 border-t">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search notifications..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Type Filter Dropdown */}
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                Type:
              </label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {notificationTypes.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>

              {/* Clear Filters Button */}
              {(searchQuery || typeFilter !== 'all' || filter !== 'all') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery('');
                    setTypeFilter('all');
                    setFilter('all');
                  }}
                  className="text-xs whitespace-nowrap"
                >
                  Clear All
                </Button>
              )}
            </div>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="p-0">
        <div className="max-h-96 overflow-y-auto">
          {filteredNotifications.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <div className="mb-4">
                <BellOff className="h-12 w-12 text-gray-400 mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchQuery || typeFilter !== 'all' ? 'No matching notifications' : 
                 filter === 'unread' ? 'No unread notifications' : 'No notifications'}
              </h3>
              <p className="text-gray-600">
                {searchQuery && `No notifications match "${searchQuery}".`}
                {typeFilter !== 'all' && !searchQuery && `No ${notificationTypes.find(t => t.value === typeFilter)?.label.toLowerCase()} notifications found.`}
                {!searchQuery && typeFilter === 'all' && filter === 'unread' && 'All notifications have been read.'}
                {!searchQuery && typeFilter === 'all' && filter === 'all' && 'No notifications yet.'}
              </p>
              {(searchQuery || typeFilter !== 'all' || filter !== 'all') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery('');
                    setTypeFilter('all');
                    setFilter('all');
                  }}
                  className="mt-3"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          ) : (
            Object.entries(groupedNotifications).map(([dateGroup, notifications]) => (
              <div key={dateGroup}>
                {/* Date Group Header */}
                <div className="sticky top-0 bg-gray-50 border-b border-gray-200 px-4 py-2 z-10">
                  <h4 className="text-sm font-semibold text-gray-700">{dateGroup}</h4>
                </div>
                
                {/* Notifications in this group */}
                <div className="divide-y divide-gray-200">
                  {notifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      onClick={() => handleNotificationClick(notification)}
                      onDismiss={(e) => handleDismiss(e, notification.id)}
                      getIcon={() => getNotificationIcon(notification.type || '', notification.priority || '')}
                      getPriorityColor={() => getPriorityColor(notification.priority || '')}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};

interface NotificationItemProps {
  notification: RealtimeNotification;
  onClick: () => void;
  onDismiss: (e: React.MouseEvent) => void;
  getIcon: () => React.ReactNode;
  getPriorityColor: () => string;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onClick,
  onDismiss,
  getIcon,
  getPriorityColor
}) => {
  return (
    <div
      onClick={onClick}
      className={`p-4 cursor-pointer transition-all duration-200 border-l-4 ${
        notification.read ? 'hover:bg-gray-50' : 'hover:bg-blue-50'
      } ${getPriorityColor()} ${
        notification.isNew ? 'animate-pulse' : ''
      } ${
        !notification.read ? 'bg-white' : 'bg-gray-50 opacity-75'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1 min-w-0">
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {getIcon()}
          </div>
          
          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <h4 className={`text-sm font-medium ${
                notification.read ? 'text-gray-700' : 'text-gray-900'
              } truncate`}>
                {notification.title}
              </h4>
              
              {/* Dismiss Button */}
              <button
                onClick={onDismiss}
                className="ml-2 p-1 rounded-full hover:bg-gray-200 transition-colors"
              >
                <X className="h-3 w-3 text-gray-400" />
              </button>
            </div>
            
            <p className={`text-sm mt-1 ${
              notification.read ? 'text-gray-500' : 'text-gray-700'
            }`}>
              {notification.message}
            </p>
            
            {/* Footer */}
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(notification.created_at)}
                </span>
                
                {/* Priority Badge */}
                {(notification.priority === 'high' || notification.priority === 'critical') && (
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    notification.priority === 'critical' 
                      ? 'bg-red-100 text-red-800' 
                      : 'bg-orange-100 text-orange-800'
                  }`}>
                    {notification.priority}
                  </span>
                )}
                
                {/* New Badge */}
                {notification.isNew && (
                  <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">
                    New
                  </span>
                )}
                
                {/* Unread Indicator */}
                {!notification.read && (
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                )}
              </div>
              
              {/* Action Link */}
              {notification.action_url && (
                <div className="flex items-center text-xs text-blue-600">
                  <ExternalLink className="h-3 w-3 mr-1" />
                  View
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};