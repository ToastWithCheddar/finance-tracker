import { Settings, Bell, Mail, Smartphone } from 'lucide-react';
import { Controller, Control } from 'react-hook-form';
import type { CreateBudgetAlertSettingsRequest } from '../../types/budgets';

interface NotificationChannelsSelectorProps {
  control: Control<CreateBudgetAlertSettingsRequest>;
}

export function NotificationChannelsSelector({ control }: NotificationChannelsSelectorProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
        <Settings className="h-4 w-4" />
        Notification Channels
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium">In-App</span>
          </div>
          <Controller
            name="in_app_alerts"
            control={control}
            render={({ field: { value, onChange } }) => (
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => onChange(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
              />
            )}
          />
        </div>

        <div className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium">Email</span>
          </div>
          <Controller
            name="email_alerts"
            control={control}
            render={({ field: { value, onChange } }) => (
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => onChange(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
              />
            )}
          />
        </div>

        <div className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="flex items-center gap-2">
            <Smartphone className="h-4 w-4 text-purple-600" />
            <span className="text-sm font-medium">Push</span>
          </div>
          <Controller
            name="push_alerts"
            control={control}
            render={({ field: { value, onChange } }) => (
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => onChange(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
              />
            )}
          />
        </div>
      </div>
    </div>
  );
}