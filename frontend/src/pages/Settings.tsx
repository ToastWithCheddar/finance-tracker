import { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui';
import { useUserPreferences, usePreferencesActions, usePreferenceOptions } from '../hooks/useUserPreferences';
import type { UserPreferences } from '../services/userPreferencesService';

export function Settings() {
  // Use the hooks for data fetching and mutations
  const { data: preferences, isLoading, error } = useUserPreferences();
  const { update, reset, isUpdating, isBusy } = usePreferencesActions();
  const options = usePreferenceOptions();
  
  // Local state for form values
  const [formData, setFormData] = useState<Partial<UserPreferences>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form data when preferences load
  useEffect(() => {
    if (preferences && Object.keys(formData).length === 0) {
      setFormData(preferences);
    }
  }, [preferences, formData]);

  const updatePreference = (key: keyof UserPreferences, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const savePreferences = () => {
    if (hasChanges) {
      update(formData, {
        onSuccess: () => {
          setHasChanges(false);
        }
      });
    }
  };

  const resetToDefaults = () => {
    reset(undefined, {
      onSuccess: (newPreferences) => {
        setFormData(newPreferences);
        setHasChanges(false);
      }
    });
  };

  const cancelChanges = () => {
    if (preferences) {
      setFormData(preferences);
      setHasChanges(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load preferences</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  if (!preferences || !formData) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">Manage your account preferences and settings</p>
        </div>

        <div className="space-y-6">
          {/* Display Preferences */}
          <Card>
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Display Preferences</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Currency</label>
                  <select
                    value={formData.currency || ''}
                    onChange={(e) => updatePreference('currency', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {options.currencies.map(currency => (
                      <option key={currency.value} value={currency.value}>
                        {currency.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Theme</label>
                  <select
                    value={formData.theme || ''}
                    onChange={(e) => updatePreference('theme', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {options.themes.map(theme => (
                      <option key={theme.value} value={theme.value}>
                        {theme.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Date Format</label>
                  <select
                    value={formData.date_format || ''}
                    onChange={(e) => updatePreference('date_format', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {options.dateFormats.map(format => (
                      <option key={format.value} value={format.value}>
                        {format.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Items per Page</label>
                  <Input
                    type="number"
                    min="10"
                    max="100"
                    value={formData.items_per_page || 25}
                    onChange={(e) => updatePreference('items_per_page', parseInt(e.target.value))}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* Notification Preferences */}
          <Card>
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Notifications</h2>
              <div className="space-y-4">
                {[
                  { key: 'email_notifications', label: 'Email Notifications', description: 'Receive notifications via email' },
                  { key: 'push_notifications', label: 'Push Notifications', description: 'Receive browser push notifications' },
                  { key: 'transaction_reminders', label: 'Transaction Reminders', description: 'Get reminders to log transactions' },
                  { key: 'budget_alerts', label: 'Budget Alerts', description: 'Alert when approaching budget limits' },
                  { key: 'weekly_reports', label: 'Weekly Reports', description: 'Receive weekly spending summaries' },
                  { key: 'monthly_reports', label: 'Monthly Reports', description: 'Receive monthly financial reports' },
                ].map(({ key, label, description }) => (
                  <div key={key} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{label}</div>
                      <div className="text-sm text-gray-500">{description}</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData[key as keyof UserPreferences] as boolean || false}
                        onChange={(e) => updatePreference(key as keyof UserPreferences, e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Financial Preferences */}
          <Card>
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Financial Settings</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Default Account Type</label>
                  <select
                    value={formData.default_account_type || ''}
                    onChange={(e) => updatePreference('default_account_type', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {options.accountTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Budget Warning Threshold (%)</label>
                  <Input
                    type="number"
                    min="0.1"
                    max="1"
                    step="0.1"
                    value={formData.budget_warning_threshold || 0.8}
                    onChange={(e) => updatePreference('budget_warning_threshold', parseFloat(e.target.value))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Low Balance Threshold</label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.low_balance_threshold || 100}
                    onChange={(e) => updatePreference('low_balance_threshold', parseFloat(e.target.value))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Startup Page</label>
                  <select
                    value={formData.startup_page || ''}
                    onChange={(e) => updatePreference('startup_page', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {options.startupPages.map(page => (
                      <option key={page.value} value={page.value}>
                        {page.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.auto_categorize || false}
                    onChange={(e) => updatePreference('auto_categorize', e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Automatically categorize transactions</span>
                </label>
              </div>
            </div>
          </Card>

          {/* Privacy & Backup */}
          <Card>
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Privacy & Backup</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900">Data Sharing</div>
                    <div className="text-sm text-gray-500">Allow anonymous data sharing for product improvement</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.data_sharing || false}
                      onChange={(e) => updatePreference('data_sharing', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900">Auto Backup</div>
                    <div className="text-sm text-gray-500">Automatically backup your data</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.auto_backup || false}
                      onChange={(e) => updatePreference('auto_backup', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Backup Frequency</label>
                  <select
                    value={formData.backup_frequency || ''}
                    onChange={(e) => updatePreference('backup_frequency', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={!formData.auto_backup}
                  >
                    {options.backupFrequencies.map(freq => (
                      <option key={freq.value} value={freq.value}>
                        {freq.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </Card>

          {/* Action Buttons */}
          <div className="flex justify-between items-center">
            <Button
              variant="outline"
              onClick={resetToDefaults}
              disabled={isBusy}
            >
              Reset to Defaults
            </Button>
            
            <div className="space-x-4">
              <Button
                variant="outline"
                onClick={cancelChanges}
                disabled={isBusy || !hasChanges}
              >
                Cancel Changes
              </Button>
              <Button
                onClick={savePreferences}
                disabled={isBusy || !hasChanges}
              >
                {isUpdating ? 'Saving...' : 'Save Preferences'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}