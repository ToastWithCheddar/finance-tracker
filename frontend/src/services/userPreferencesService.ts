import { apiClient } from './api';

export interface UserPreferences {
  // Display preferences
  currency: string;
  date_format: string;
  number_format: string;
  theme: string;
  
  // Notification preferences
  email_notifications: boolean;
  push_notifications: boolean;
  transaction_reminders: boolean;
  budget_alerts: boolean;
  weekly_reports: boolean;
  monthly_reports: boolean;
  
  // Privacy preferences
  data_sharing: boolean;
  analytics_tracking: boolean;
  
  // Financial preferences
  default_account_type: string;
  budget_warning_threshold: number;
  low_balance_threshold: number;
  
  // Backup preferences
  auto_backup: boolean;
  backup_frequency: string;
  
  // App preferences
  startup_page: string;
  items_per_page: number;
  auto_categorize: boolean;
}

export interface UserPreferencesUpdate extends Partial<UserPreferences> {
  // Explicitly allow partial updates of UserPreferences
}

export interface UserPreferencesResponse extends UserPreferences {
  user_id: string;
  created_at: string;
  updated_at: string;
}

export const defaultPreferences: UserPreferences = {
  currency: 'USD',
  date_format: 'MM/DD/YYYY',
  number_format: 'en-US',
  theme: 'light',
  email_notifications: true,
  push_notifications: true,
  transaction_reminders: false,
  budget_alerts: true,
  weekly_reports: false,
  monthly_reports: true,
  data_sharing: false,
  analytics_tracking: true,
  default_account_type: 'checking',
  budget_warning_threshold: 0.8,
  low_balance_threshold: 100.0,
  auto_backup: true,
  backup_frequency: 'weekly',
  startup_page: 'dashboard',
  items_per_page: 25,
  auto_categorize: true,
};

class UserPreferencesService {
  async getPreferences(): Promise<UserPreferencesResponse> {
    try {
      return await apiClient.get<UserPreferencesResponse>('/users/me/preferences');
    } catch (error) {
      // If preferences don't exist yet, return defaults with fallback data
      console.warn('Failed to load user preferences, using defaults:', error);
      
      // Create default preferences on the server
      try {
        return await this.updatePreferences(defaultPreferences);
      } catch (createError) {
        console.error('Failed to create default preferences:', createError);
        throw error;
      }
    }
  }

  async updatePreferences(preferences: UserPreferencesUpdate): Promise<UserPreferencesResponse> {
    return apiClient.put<UserPreferencesResponse>('/users/me/preferences', preferences);
  }

  async resetToDefaults(): Promise<UserPreferencesResponse> {
    return this.updatePreferences(defaultPreferences);
  }

  // Helper methods for working with preferences
  getCurrencyOptions(): Array<{ value: string; label: string }> {
    return [
      { value: 'USD', label: 'USD - US Dollar' },
      { value: 'EUR', label: 'EUR - Euro' },
      { value: 'GBP', label: 'GBP - British Pound' },
      { value: 'JPY', label: 'JPY - Japanese Yen' },
      { value: 'CAD', label: 'CAD - Canadian Dollar' },
      { value: 'AUD', label: 'AUD - Australian Dollar' },
      { value: 'CHF', label: 'CHF - Swiss Franc' },
      { value: 'CNY', label: 'CNY - Chinese Yuan' },
    ];
  }

  getDateFormatOptions(): Array<{ value: string; label: string }> {
    return [
      { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (US)' },
      { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (UK)' },
      { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (ISO)' },
      { value: 'DD.MM.YYYY', label: 'DD.MM.YYYY (German)' },
    ];
  }

  getThemeOptions(): Array<{ value: string; label: string }> {
    return [
      { value: 'light', label: 'Light' },
      { value: 'dark', label: 'Dark' },
      { value: 'auto', label: 'Auto (System)' },
    ];
  }

  getAccountTypeOptions(): Array<{ value: string; label: string }> {
    return [
      { value: 'checking', label: 'Checking Account' },
      { value: 'savings', label: 'Savings Account' },
      { value: 'credit', label: 'Credit Card' },
      { value: 'cash', label: 'Cash' },
      { value: 'investment', label: 'Investment Account' },
    ];
  }

  getBackupFrequencyOptions(): Array<{ value: string; label: string }> {
    return [
      { value: 'daily', label: 'Daily' },
      { value: 'weekly', label: 'Weekly' },
      { value: 'monthly', label: 'Monthly' },
    ];
  }

  getStartupPageOptions(): Array<{ value: string; label: string }> {
    return [
      { value: 'dashboard', label: 'Dashboard' },
      { value: 'transactions', label: 'Transactions' },
      { value: 'budgets', label: 'Budgets' },
      { value: 'categories', label: 'Categories' },
      { value: 'settings', label: 'Settings' },
    ];
  }

  formatCurrency(amount: number, currency: string = 'USD'): string {
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
      }).format(amount);
    } catch {
      // Fallback if currency is not supported
      return `${currency} ${amount.toFixed(2)}`;
    }
  }

  formatDate(date: Date | string, format: string = 'MM/DD/YYYY'): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    const day = dateObj.getDate().toString().padStart(2, '0');
    const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
    const year = dateObj.getFullYear().toString();
    
    switch (format) {
      case 'DD/MM/YYYY':
        return `${day}/${month}/${year}`;
      case 'YYYY-MM-DD':
        return `${year}-${month}-${day}`;
      case 'DD.MM.YYYY':
        return `${day}.${month}.${year}`;
      case 'MM/DD/YYYY':
      default:
        return `${month}/${day}/${year}`;
    }
  }

  validatePreferences(preferences: Partial<UserPreferences>): string[] {
    const errors: string[] = [];

    if (preferences.budget_warning_threshold !== undefined) {
      if (preferences.budget_warning_threshold < 0 || preferences.budget_warning_threshold > 1) {
        errors.push('Budget warning threshold must be between 0 and 1');
      }
    }

    if (preferences.low_balance_threshold !== undefined) {
      if (preferences.low_balance_threshold < 0) {
        errors.push('Low balance threshold cannot be negative');
      }
    }

    if (preferences.items_per_page !== undefined) {
      if (preferences.items_per_page < 5 || preferences.items_per_page > 100) {
        errors.push('Items per page must be between 5 and 100');
      }
    }

    return errors;
  }

  // Local storage fallback methods (for backward compatibility or offline use)
  getLocalPreferences(): UserPreferences {
    const stored = localStorage.getItem('user_preferences');
    if (stored) {
      try {
        return { ...defaultPreferences, ...JSON.parse(stored) };
      } catch (error) {
        console.warn('Failed to parse stored preferences:', error);
      }
    }
    return defaultPreferences;
  }

  setLocalPreferences(preferences: UserPreferences): void {
    try {
      localStorage.setItem('user_preferences', JSON.stringify(preferences));
    } catch (error) {
      console.warn('Failed to store preferences locally:', error);
    }
  }

  clearLocalPreferences(): void {
    localStorage.removeItem('user_preferences');
  }
}

export const userPreferencesService = new UserPreferencesService();