import { Zap, Clock } from 'lucide-react';
import { Controller, Control } from 'react-hook-form';
import type { CreateBudgetAlertSettingsRequest } from '../../types/budgets';

interface SmartFeaturesSettingsProps {
  control: Control<CreateBudgetAlertSettingsRequest>;
}

export function SmartFeaturesSettings({ control }: SmartFeaturesSettingsProps) {
  return (
    <>
      {/* Alert Frequency */}
      <div className="space-y-4">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Alert Frequency
        </h3>
        
        <Controller
          name="alert_frequency"
          control={control}
          render={({ field }) => (
            <select
              {...field}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="immediate">Immediate</option>
              <option value="daily">Daily Digest</option>
              <option value="weekly">Weekly Summary</option>
            </select>
          )}
        />
      </div>

      {/* Smart Features */}
      <div className="space-y-4">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <Zap className="h-4 w-4" />
          Smart Features
        </h3>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Suppress Repeated Alerts
              </label>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Avoid duplicate notifications for the same threshold
              </p>
            </div>
            <Controller
              name="suppress_repeated_alerts"
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

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                End of Period Warning
              </label>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Alert when budget period is ending
              </p>
            </div>
            <Controller
              name="end_of_period_warning"
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

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Smart Pacing Alerts
              </label>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Alert if spending pace will exceed budget
              </p>
            </div>
            <Controller
              name="smart_pacing_alerts"
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

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Milestone Celebrations
              </label>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Celebrate staying within budget goals
              </p>
            </div>
            <Controller
              name="milestone_celebration"
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
    </>
  );
}