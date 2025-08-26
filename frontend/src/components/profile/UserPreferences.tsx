import { useState } from 'react';
import { Settings, Save, Sun, Moon, Bell, BellOff, Globe, DollarSign, List, TrendingUp, Brain } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui';
import { userService, type UserProfile, type UserUpdateData } from '../../services/userService';

interface UserPreferencesProps {
  profile: UserProfile;
  onUpdate: (updatedProfile: UserProfile) => void;
}

export function UserPreferences({ profile, onUpdate }: UserPreferencesProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [preferences, setPreferences] = useState({
    theme: profile.theme,
    notifications_enabled: profile.notifications_enabled,
    auto_categorization_enabled: profile.auto_categorization_enabled,
    locale: profile.locale,
    timezone: profile.timezone,
    currency: profile.currency,
    default_items_per_page: profile.default_items_per_page,
    spending_alert_threshold_cents: profile.spending_alert_threshold_cents || null,
  });

  const handleSave = async () => {
    try {
      setIsLoading(true);
      
      const updateData: UserUpdateData = {
        theme: preferences.theme,
        notifications_enabled: preferences.notifications_enabled,
        auto_categorization_enabled: preferences.auto_categorization_enabled,
        locale: preferences.locale,
        timezone: preferences.timezone,
        currency: preferences.currency,
        default_items_per_page: preferences.default_items_per_page,
        spending_alert_threshold_cents: preferences.spending_alert_threshold_cents,
      };
      
      const updatedProfile = await userService.updateProfile(updateData);
      onUpdate(updatedProfile);
      
      // Update local preferences state with returned values
      setPreferences({
        theme: updatedProfile.theme,
        notifications_enabled: updatedProfile.notifications_enabled,
        auto_categorization_enabled: updatedProfile.auto_categorization_enabled,
        locale: updatedProfile.locale,
        timezone: updatedProfile.timezone,
        currency: updatedProfile.currency,
        default_items_per_page: updatedProfile.default_items_per_page,
        spending_alert_threshold_cents: updatedProfile.spending_alert_threshold_cents || null,
      });
    } catch (error) {
      console.error('Failed to update preferences:', error);
      alert('Failed to update preferences. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (key: string, value: any) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const timezones = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Australia/Sydney',
  ];

  const currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY'];
  const itemsPerPageOptions = [10, 25, 50, 100];

  return (
    <Card>
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Settings className="h-6 w-6 text-[hsl(var(--brand))]" />
          <h2 className="text-xl font-semibold text-[hsl(var(--text))]">User Preferences</h2>
        </div>

        <div className="space-y-6">
          {/* Appearance Settings */}
          <div>
            <h3 className="text-lg font-medium text-[hsl(var(--text))] mb-3">Appearance</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {preferences.theme === 'dark' ? (
                    <Moon className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  ) : (
                    <Sun className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  )}
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Theme</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Choose light or dark mode</div>
                  </div>
                </div>
                <button
                  onClick={() => handleChange('theme', preferences.theme === 'light' ? 'dark' : 'light')}
                  className={`relative inline-flex items-center h-6 rounded-full w-12 transition-colors focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] focus:ring-offset-2 ${
                    preferences.theme === 'dark' ? 'bg-[hsl(var(--brand))]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-flex items-center justify-center w-4 h-4 transform bg-white rounded-full transition-transform ${
                      preferences.theme === 'dark' ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  >
                    {preferences.theme === 'dark' ? (
                      <Moon className="h-3 w-3 text-gray-600" />
                    ) : (
                      <Sun className="h-3 w-3 text-yellow-500" />
                    )}
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div>
            <h3 className="text-lg font-medium text-[hsl(var(--text))] mb-3">Notifications</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {preferences.notifications_enabled ? (
                    <Bell className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  ) : (
                    <BellOff className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  )}
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Notifications</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Enable budget alerts and goal milestones</div>
                  </div>
                </div>
                <button
                  onClick={() => handleChange('notifications_enabled', !preferences.notifications_enabled)}
                  className={`relative inline-flex items-center h-6 rounded-full w-12 transition-colors focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] focus:ring-offset-2 ${
                    preferences.notifications_enabled ? 'bg-[hsl(var(--brand))]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform ${
                      preferences.notifications_enabled ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Localization */}
          <div>
            <h3 className="text-lg font-medium text-[hsl(var(--text))] mb-3">Localization</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Globe className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Timezone</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Your local timezone</div>
                  </div>
                </div>
                <select
                  value={preferences.timezone}
                  onChange={(e) => handleChange('timezone', e.target.value)}
                  className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium text-[hsl(var(--text))] min-w-[160px] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))] transition-all"
                >
                  {timezones.map(tz => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <DollarSign className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Currency</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Default currency</div>
                  </div>
                </div>
                <select
                  value={preferences.currency}
                  onChange={(e) => handleChange('currency', e.target.value)}
                  className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium text-[hsl(var(--text))] min-w-[90px] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))] transition-all"
                >
                  {currencies.map(curr => (
                    <option key={curr} value={curr}>{curr}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Display Settings */}
          <div>
            <h3 className="text-lg font-medium text-[hsl(var(--text))] mb-3">Display Preferences</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <List className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Items per page</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Number of transactions to show</div>
                  </div>
                </div>
                <select
                  value={preferences.default_items_per_page}
                  onChange={(e) => handleChange('default_items_per_page', Number(e.target.value))}
                  className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium text-[hsl(var(--text))] min-w-[100px] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))] transition-all"
                >
                  {itemsPerPageOptions.map(count => (
                    <option key={count} value={count}>{count} items</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Financial Preferences */}
          <div>
            <h3 className="text-lg font-medium text-[hsl(var(--text))] mb-3">Financial Preferences</h3>
            <div className="space-y-4">
              
              {/* ML Auto-categorization Toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Brain className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Smart Categorization</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Automatically categorize transactions using AI</div>
                  </div>
                </div>
                <button
                  onClick={() => handleChange('auto_categorization_enabled', !preferences.auto_categorization_enabled)}
                  className={`relative inline-flex items-center h-6 rounded-full w-12 transition-colors focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] focus:ring-offset-2 ${
                    preferences.auto_categorization_enabled ? 'bg-[hsl(var(--brand))]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform ${
                      preferences.auto_categorization_enabled ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Spending Alert Threshold</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Alert when spending exceeds this amount (in dollars)</div>
                  </div>
                </div>
                <input
                  type="number"
                  value={preferences.spending_alert_threshold_cents ? preferences.spending_alert_threshold_cents / 100 : ''}
                  onChange={(e) => {
                    const value = e.target.value;
                    handleChange('spending_alert_threshold_cents', value ? Number(value) * 100 : null);
                  }}
                  placeholder="No limit"
                  min="0"
                  step="0.01"
                  className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-[hsl(var(--text))] w-32"
                />
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4 border-t border-[hsl(var(--border))]">
            <Button 
              onClick={handleSave}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <LoadingSpinner size="sm" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Preferences
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}