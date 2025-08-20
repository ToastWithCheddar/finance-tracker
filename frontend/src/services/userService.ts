import { apiClient } from './api';
import type { ActivityEvent, ActivityFeedOptions, ActivityResponse } from '../types/activity';

export interface UserUpdateData {
  first_name?: string;
  last_name?: string;
  display_name?: string;
  avatar_url?: string;
  [key: string]: unknown;
}

export interface UserProfile {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  display_name?: string;
  avatar_url?: string;
  locale: string;
  timezone: string;
  currency: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string;
}

export interface UserStats {
  total_transactions: number;
  total_accounts: number;
  account_age_days: number;
  last_login?: string;
  data_usage_mb: number;
}

export class UserService {
  /**
   * Get current user's profile
   */
  async getCurrentUserProfile(): Promise<UserProfile> {
    return apiClient.get<UserProfile>('/users/me');
  }

  /**
   * Update current user's profile
   */
  async updateProfile(data: UserUpdateData): Promise<UserProfile> {
    return apiClient.put<UserProfile>('/users/me', data);
  }

  /**
   * Upload user avatar
   */
  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    const formData = new FormData();
    formData.append('avatar', file);
    
    return apiClient.postFormData<{ avatar_url: string }>('/users/me/avatar', formData);
  }

  /**
   * Remove user avatar
   */
  async removeAvatar(): Promise<UserProfile> {
    return apiClient.put<UserProfile>('/users/me', { avatar_url: null });
  }

  /**
   * Get user account statistics
   */
  async getUserStats(): Promise<UserStats> {
    return apiClient.get<UserStats>('/users/me/stats');
  }

  /**
   * Export user data
   */
  async exportUserData(): Promise<Blob> {
    return apiClient.getBlob('/users/me/export');
  }

  /**
   * Deactivate user account
   */
  async deactivateAccount(): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>('/users/me');
  }

  /**
   * Change password
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    });
  }

  /**
   * Get user sessions
   */
  async getUserSessions(): Promise<Array<{
    id: string;
    device: string;
    location: string;
    last_active: string;
    is_current: boolean;
  }>> {
    return apiClient.get('/users/me/sessions');
  }

  /**
   * Revoke user session
   */
  async revokeSession(sessionId: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/users/me/sessions/${sessionId}`);
  }

  /**
   * Revoke all sessions except current
   */
  async revokeAllSessions(): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/users/me/sessions/revoke-all');
  }

  /**
   * Get user activity feed
   */
  async getActivityFeed(options: ActivityFeedOptions = {}): Promise<ActivityResponse> {
    const params = new URLSearchParams();
    
    if (options.limit) {
      params.append('limit', options.limit.toString());
    }
    if (options.table_name) {
      params.append('table_name', options.table_name);
    }
    if (options.since) {
      params.append('since', options.since);
    }

    const queryString = params.toString();
    const url = `/users/me/activity${queryString ? `?${queryString}` : ''}`;
    
    return apiClient.get<ActivityResponse>(url);
  }
}

// Export singleton instance
export const userService = new UserService();