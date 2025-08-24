import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { X, Bell, Save, Trash2, Settings2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Modal } from '../ui/Modal';
import { AlertTestingSection } from './AlertTestingSection';
import { SmartFeaturesSettings } from './SmartFeaturesSettings';
import { useBudgetAlertSettings, useBudgetAlertActions } from '../../hooks/useBudgetAlerts';
import { budgetAlertService } from '../../services/budgetAlertService';
import type { Budget, CreateBudgetAlertSettingsRequest } from '../../types/budgets';
import { toast } from 'react-hot-toast';

interface BudgetAlertSettingsProps {
  budget: Budget;
  isOpen: boolean;
  onClose: () => void;
}

export function BudgetAlertSettings({ budget, isOpen, onClose }: BudgetAlertSettingsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const { data: alertSettings, isLoading: isLoadingSettings } = useBudgetAlertSettings(budget.id);
  const alertActions = useBudgetAlertActions();

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
    control,
    watch
  } = useForm<CreateBudgetAlertSettingsRequest>();

  // Load settings into form when data is available
  useEffect(() => {
    if (isOpen && alertSettings) {
      reset({
        alerts_enabled: alertSettings.alerts_enabled,
        alert_thresholds: alertSettings.alert_thresholds,
        alert_frequency: alertSettings.alert_frequency,
        suppress_repeated_alerts: alertSettings.suppress_repeated_alerts,
        end_of_period_warning: alertSettings.end_of_period_warning,
        end_warning_days: alertSettings.end_warning_days,
        smart_pacing_alerts: alertSettings.smart_pacing_alerts,
        milestone_celebration: alertSettings.milestone_celebration,
      });
    } else if (isOpen && !alertSettings && !isLoadingSettings) {
      // Load defaults if no existing settings
      const defaults = budgetAlertService.getDefaultAlertSettings(budget.id);
      reset(defaults);
    }
  }, [alertSettings, isOpen, isLoadingSettings, reset, budget.id]);

  const watchedThresholds = watch('alert_thresholds') || [];
  const watchedEnabled = watch('alerts_enabled');

  const onSubmit = (data: CreateBudgetAlertSettingsRequest) => {
    if (alertSettings) {
      // Update existing settings
      alertActions.update({
        budgetId: budget.id,
        settings: data
      });
    } else {
      // Create new settings
      alertActions.create({
        budgetId: budget.id,
        settings: data
      });
    }
  };

  const handleDelete = () => {
    if (alertSettings) {
      alertActions.delete(budget.id);
      toast.success('Alert settings removed');
      onClose();
    }
  };

  const addThreshold = () => {
    const currentThresholds = watchedThresholds;
    if (currentThresholds.length < 10) {
      const newThreshold = 0.8;
      reset({
        ...watch(),
        alert_thresholds: [...currentThresholds, newThreshold].sort((a, b) => a - b)
      });
    }
  };

  const removeThreshold = (index: number) => {
    const currentThresholds = watchedThresholds;
    if (currentThresholds.length > 1) {
      const newThresholds = currentThresholds.filter((_, i) => i !== index);
      reset({
        ...watch(),
        alert_thresholds: newThresholds
      });
    }
  };

  const updateThreshold = (index: number, value: number) => {
    const currentThresholds = [...watchedThresholds];
    currentThresholds[index] = value;
    reset({
      ...watch(),
      alert_thresholds: currentThresholds.sort((a, b) => a - b)
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-800 rounded-lg">
                <Bell className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <CardTitle>Alert Settings</CardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Configure alerts for "{budget.name}"
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Enable Alerts Toggle */}
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
              <div>
                <h3 className="font-medium text-gray-900 dark:text-gray-100">
                  Enable Budget Alerts
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Get notified when spending approaches your thresholds
                </p>
              </div>
              <Controller
                name="alerts_enabled"
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

            {watchedEnabled && (
              <>
                {/* Alert Thresholds */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-gray-900 dark:text-gray-100">
                      Alert Thresholds
                    </h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addThreshold}
                      disabled={watchedThresholds.length >= 10}
                    >
                      Add Threshold
                    </Button>
                  </div>
                  
                  <div className="space-y-3">
                    {watchedThresholds.map((threshold, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <div className="flex-1">
                          <Controller
                            name={`alert_thresholds.${index}`}
                            control={control}
                            render={({ field: { value, onChange } }) => (
                              <input
                                type="range"
                                min="0.1"
                                max="1.0"
                                step="0.05"
                                value={value || 0.8}
                                onChange={(e) => {
                                  const newValue = parseFloat(e.target.value);
                                  onChange(newValue);
                                  updateThreshold(index, newValue);
                                }}
                                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                              />
                            )}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 w-12">
                          {budgetAlertService.formatAlertThreshold(threshold)}
                        </span>
                        {watchedThresholds.length > 1 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeThreshold(index)}
                            className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Smart Features */}
                <SmartFeaturesSettings control={control} />

                {/* Advanced Settings */}
                <div className="space-y-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-2"
                  >
                    <Settings2 className="h-4 w-4" />
                    {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
                  </Button>

                  {showAdvanced && (
                    <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                      {/* End of Period Warning Days */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          End Warning Days ({watch('end_warning_days') || 3} days)
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="14"
                          step="1"
                          {...register('end_warning_days')}
                          className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                          <span>1 day</span>
                          <span>14 days</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Alert Testing */}
                <AlertTestingSection budget={budget} />
              </>
            )}

            {/* Form Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-600">
              <div>
                {alertSettings && (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleDelete}
                    disabled={alertActions.isDeleting}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Remove All Alerts
                  </Button>
                )}
              </div>
              
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={onClose}
                  disabled={alertActions.isCreating || alertActions.isUpdating}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!isDirty || alertActions.isCreating || alertActions.isUpdating}
                >
                  <Save className="h-4 w-4 mr-2" />
                  {alertActions.isCreating || alertActions.isUpdating 
                    ? 'Saving...' 
                    : alertSettings ? 'Update Settings' : 'Create Settings'
                  }
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </Modal>
  );
}