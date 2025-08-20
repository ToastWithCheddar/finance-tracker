import { AlertTriangle, Check } from 'lucide-react';
import { BudgetAlertService } from '../../services/budgetAlertService';

interface AlertThresholdsSelectorProps {
  selectedThresholds: number[];
  onThresholdToggle: (threshold: number) => void;
}

export function AlertThresholdsSelector({ 
  selectedThresholds, 
  onThresholdToggle 
}: AlertThresholdsSelectorProps) {
  const predefinedThresholds = BudgetAlertService.getPredefinedThresholds();

  return (
    <div className="space-y-4">
      <h3 className="font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4" />
        Alert Thresholds
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Select when you want to be notified based on spending percentage
      </p>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {predefinedThresholds.map(({ value, label, color }) => {
          const isSelected = selectedThresholds.includes(value);
          return (
            <button
              key={value}
              type="button"
              onClick={() => onThresholdToggle(value)}
              className={`
                p-3 rounded-lg border-2 transition-all duration-200
                ${isSelected 
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }
              `}
            >
              <div className="flex items-center justify-between">
                <span className={`px-2 py-1 rounded text-xs font-medium ${color}`}>
                  {label}
                </span>
                {isSelected && (
                  <Check className="h-4 w-4 text-primary-600" />
                )}
              </div>
            </button>
          );
        })}
      </div>
      
      {selectedThresholds.length === 0 && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Please select at least one threshold
        </p>
      )}
    </div>
  );
}