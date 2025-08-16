import { apiClient } from './api';

export interface NotificationResponse {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: 'budget_alert' | 'goal_milestone' | 'goal_achieved' | 'transaction_alert' | 'system_alert' | 'info';
  priority: 'low' | 'medium' | 'high' | 'critical';
  is_read: boolean;
  action_url?: string;
  extra_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationResponse[];
  total: number;
  unread_count: number;
  skip: number;
  limit: number;
}

export interface NotificationStatsResponse {
  total_count: number;
  unread_count: number;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface NotificationFilters {
  skip?: number;
  limit?: number;
  unread_only?: boolean;
  type_filter?: string;
}

export interface BulkMarkReadResponse {
  updated_count: number;
  success: boolean;
}

export class NotificationService {
  /**
   * Get notifications for the current user with optional filtering
   */
  static async getNotifications(filters: NotificationFilters = {}): Promise<NotificationListResponse> {
    const params = new URLSearchParams();
    
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
    if (filters.unread_only) params.append('unread_only', 'true');
    if (filters.type_filter) params.append('type_filter', filters.type_filter);
    
    return await apiClient.get<NotificationListResponse>(`/notifications?${params.toString()}`);
  }

  /**
   * Get notification statistics
   */
  static async getNotificationStats(): Promise<NotificationStatsResponse> {
    return await apiClient.get<NotificationStatsResponse>('/notifications/stats');
  }

  /**
   * Get a specific notification by ID
   */
  static async getNotification(id: string): Promise<NotificationResponse> {
    return await apiClient.get<NotificationResponse>(`/notifications/${id}`);
  }

  /**
   * Mark a notification as read
   */
  static async markAsRead(id: string): Promise<NotificationResponse> {
    return await apiClient.patch<NotificationResponse>(`/notifications/${id}`, {
      is_read: true
    });
  }

  /**
   * Mark a notification as unread
   */
  static async markAsUnread(id: string): Promise<NotificationResponse> {
    return await apiClient.patch<NotificationResponse>(`/notifications/${id}`, {
      is_read: false
    });
  }

  /**
   * Dismiss (delete) a notification
   */
  static async dismissNotification(id: string): Promise<void> {
    await apiClient.delete(`/notifications/${id}`);
  }

  /**
   * Mark all notifications as read
   */
  static async markAllAsRead(): Promise<BulkMarkReadResponse> {
    return await apiClient.post<BulkMarkReadResponse>('/notifications/mark-all-read');
  }

  /**
   * Get unread count only (lightweight)
   */
  static async getUnreadCount(): Promise<number> {
    const response = await apiClient.get<NotificationListResponse>('/notifications?limit=1&unread_only=true');
    return response.unread_count;
  }

  /**
   * Batch mark notifications as read
   */
  static async batchMarkAsRead(ids: string[]): Promise<BulkMarkReadResponse> {
    // Since we don't have batch endpoint, mark individually
    let updated_count = 0;
    for (const id of ids) {
      try {
        await this.markAsRead(id);
        updated_count++;
      } catch (error) {
        console.error(`Failed to mark notification ${id} as read:`, error);
      }
    }
    
    return {
      updated_count,
      success: updated_count > 0
    };
  }

  /**
   * Filter notifications by type
   */
  static async getNotificationsByType(type: string, filters: Omit<NotificationFilters, 'type_filter'> = {}): Promise<NotificationListResponse> {
    return this.getNotifications({
      ...filters,
      type_filter: type
    });
  }

  /**
   * Get only unread notifications
   */
  static async getUnreadNotifications(filters: Omit<NotificationFilters, 'unread_only'> = {}): Promise<NotificationListResponse> {
    return this.getNotifications({
      ...filters,
      unread_only: true
    });
  }
}

export default NotificationService;