import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { NotificationService, NotificationFilters, NotificationResponse } from '../services/notificationService';
import { toast } from 'react-hot-toast';

// Query keys for React Query
export const NOTIFICATION_KEYS = {
  all: ['notifications'] as const,
  lists: () => [...NOTIFICATION_KEYS.all, 'list'] as const,
  list: (filters: NotificationFilters) => [...NOTIFICATION_KEYS.lists(), filters] as const,
  stats: () => [...NOTIFICATION_KEYS.all, 'stats'] as const,
  unread: () => [...NOTIFICATION_KEYS.all, 'unread'] as const,
  detail: (id: string) => [...NOTIFICATION_KEYS.all, 'detail', id] as const,
};

/**
 * Hook to fetch notifications with optional filtering
 */
export function useNotifications(filters: NotificationFilters = {}) {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.list(filters),
    queryFn: () => NotificationService.getNotifications(filters),
    staleTime: 1000 * 60, // 1 minute
    refetchOnWindowFocus: true,
  });
}

/**
 * Hook to fetch notification statistics
 */
export function useNotificationStats() {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.stats(),
    queryFn: () => NotificationService.getNotificationStats(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook to fetch unread count only
 */
export function useUnreadCount() {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.unread(),
    queryFn: () => NotificationService.getUnreadCount(),
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 60, // Refresh every minute
  });
}

/**
 * Hook to fetch a specific notification
 */
export function useNotification(id: string) {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.detail(id),
    queryFn: () => NotificationService.getNotification(id),
    enabled: !!id,
  });
}

/**
 * Hook to mark a notification as read
 */
export function useMarkAsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => NotificationService.markAsRead(id),
    onSuccess: (updatedNotification) => {
      // Update specific notification queries
      queryClient.setQueryData(
        NOTIFICATION_KEYS.detail(updatedNotification.id),
        updatedNotification
      );

      // Invalidate list queries to refresh unread counts
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.lists() });
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.stats() });
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.unread() });
    },
    onError: (error) => {
      console.error('Failed to mark notification as read:', error);
      toast.error('Failed to mark notification as read');
    },
  });
}

/**
 * Hook to mark a notification as unread
 */
export function useMarkAsUnread() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => NotificationService.markAsUnread(id),
    onSuccess: (updatedNotification) => {
      // Update specific notification queries
      queryClient.setQueryData(
        NOTIFICATION_KEYS.detail(updatedNotification.id),
        updatedNotification
      );

      // Invalidate list queries to refresh unread counts
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.lists() });
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.stats() });
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.unread() });
    },
    onError: (error) => {
      console.error('Failed to mark notification as unread:', error);
      toast.error('Failed to mark notification as unread');
    },
  });
}

/**
 * Hook to dismiss a notification
 */
export function useDismissNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => NotificationService.dismissNotification(id),
    onSuccess: (_, dismissedId) => {
      // Remove from specific notification cache
      queryClient.removeQueries({ queryKey: NOTIFICATION_KEYS.detail(dismissedId) });

      // Invalidate list queries to remove from lists
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.lists() });
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.stats() });
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.unread() });

      toast.success('Notification dismissed');
    },
    onError: (error) => {
      console.error('Failed to dismiss notification:', error);
      toast.error('Failed to dismiss notification');
    },
  });
}

/**
 * Hook to mark all notifications as read
 */
export function useMarkAllAsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => NotificationService.markAllAsRead(),
    onSuccess: (result) => {
      // Invalidate all notification queries
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_KEYS.all });
      
      toast.success(`Marked ${result.updated_count} notifications as read`);
    },
    onError: (error) => {
      console.error('Failed to mark all notifications as read:', error);
      toast.error('Failed to mark all notifications as read');
    },
  });
}

/**
 * Hook to get unread notifications only
 */
export function useUnreadNotifications(filters: Omit<NotificationFilters, 'unread_only'> = {}) {
  return useNotifications({ ...filters, unread_only: true });
}

/**
 * Hook to get notifications by type
 */
export function useNotificationsByType(
  type: string, 
  filters: Omit<NotificationFilters, 'type_filter'> = {}
) {
  return useNotifications({ ...filters, type_filter: type });
}

/**
 * Combined hook for notification management
 */
export function useNotificationActions() {
  const markAsRead = useMarkAsRead();
  const markAsUnread = useMarkAsUnread();
  const dismiss = useDismissNotification();
  const markAllAsRead = useMarkAllAsRead();

  return {
    markAsRead: markAsRead.mutate,
    markAsUnread: markAsUnread.mutate,
    dismiss: dismiss.mutate,
    markAllAsRead: markAllAsRead.mutate,
    
    // Loading states
    isMarkingAsRead: markAsRead.isPending,
    isMarkingAsUnread: markAsUnread.isPending,
    isDismissing: dismiss.isPending,
    isMarkingAllAsRead: markAllAsRead.isPending,
  };
}

/**
 * Hook for notification display helpers
 */
export function useNotificationHelpers() {
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    if (diffInMinutes < 10080) return `${Math.floor(diffInMinutes / 1440)}d ago`;
    
    return date.toLocaleDateString();
  };

  const getPriorityColor = (priority: NotificationResponse['priority']) => {
    switch (priority) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      case 'low': return 'blue';
      default: return 'gray';
    }
  };

  const getTypeIcon = (type: NotificationResponse['type']) => {
    switch (type) {
      case 'budget_alert': return '💰';
      case 'goal_milestone': return '🎯';
      case 'goal_achieved': return '🎉';
      case 'transaction_alert': return '💳';
      case 'system_alert': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '📢';
    }
  };

  return {
    formatTime,
    getPriorityColor,
    getTypeIcon,
  };
}

export default {
  useNotifications,
  useNotificationStats,
  useUnreadCount,
  useNotification,
  useMarkAsRead,
  useMarkAsUnread,
  useDismissNotification,
  useMarkAllAsRead,
  useUnreadNotifications,
  useNotificationsByType,
  useNotificationActions,
  useNotificationHelpers,
};