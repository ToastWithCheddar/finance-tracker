import { useState } from 'react';
import { Calendar } from 'lucide-react';
import { Button } from '../ui';
import type { DashboardFilters as FilterType } from '../../services/dashboardService';

interface DashboardFiltersProps {
  filters: FilterType;
  onFiltersChange: (filters: FilterType) => void;
}

const PREDEFINED_RANGES = [
  { key: 'today', label: 'Today' },
  { key: 'thisWeek', label: 'This Week' },
  { key: 'thisMonth', label: 'This Month' },
  { key: 'lastMonth', label: 'Last Month' },
  { key: 'thisYear', label: 'This Year' },
  { key: 'last30Days', label: 'Last 30 Days' },
] as const;

export function DashboardFilters({ filters, onFiltersChange }: DashboardFiltersProps) {
  const [showCustomRange, setShowCustomRange] = useState(false);
  const [customStartDate, setCustomStartDate] = useState(filters.start_date || '');
  const [customEndDate, setCustomEndDate] = useState(filters.end_date || '');

  const getDateRangePresets = () => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    
    // This week
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    const thisWeekStart = startOfWeek.toISOString().split('T')[0];
    
    // This month
    const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
    
    // Last month
    const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0).toISOString().split('T')[0];
    
    // This year
    const thisYearStart = new Date(now.getFullYear(), 0, 1).toISOString().split('T')[0];
    
    // Last 30 days
    const last30Days = new Date(now);
    last30Days.setDate(now.getDate() - 30);
    const last30DaysStart = last30Days.toISOString().split('T')[0];

    return {
      today: { start_date: today, end_date: today },
      thisWeek: { start_date: thisWeekStart, end_date: today },
      thisMonth: { start_date: thisMonthStart, end_date: today },
      lastMonth: { start_date: lastMonthStart, end_date: lastMonthEnd },
      thisYear: { start_date: thisYearStart, end_date: today },
      last30Days: { start_date: last30DaysStart, end_date: today },
    };
  };

  const handlePredefinedRangeClick = (rangeKey: string) => {
    const presets = getDateRangePresets();
    const range = presets[rangeKey as keyof typeof presets];
    
    if (range) {
      onFiltersChange({
        ...filters,
        start_date: range.start_date,
        end_date: range.end_date,
      });
      setShowCustomRange(false);
    }
  };

  const handleCustomRangeSubmit = () => {
    if (customStartDate && customEndDate) {
      onFiltersChange({
        ...filters,
        start_date: customStartDate,
        end_date: customEndDate,
      });
      setShowCustomRange(false);
    }
  };

  const formatDateRange = () => {
    if (!filters.start_date || !filters.end_date) return 'Select Date Range';
    
    const start = new Date(filters.start_date).toLocaleDateString();
    const end = new Date(filters.end_date).toLocaleDateString();
    
    if (start === end) return start;
    return `${start} - ${end}`;
  };

  const getCurrentRangeLabel = () => {
    const presets = getDateRangePresets();
    
    for (const range of PREDEFINED_RANGES) {
      const preset = presets[range.key];
      if (preset.start_date === filters.start_date && preset.end_date === filters.end_date) {
        return range.label;
      }
    }
    
    return formatDateRange();
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Time Period:</span>
        </div>
        
        <div className="flex flex-wrap gap-2">
          {PREDEFINED_RANGES.map((range) => (
            <Button
              key={range.key}
              variant={getCurrentRangeLabel() === range.label ? "primary" : "outline"}
              size="sm"
              onClick={() => handlePredefinedRangeClick(range.key)}
              className="text-xs"
            >
              {range.label}
            </Button>
          ))}
          
          <Button
            variant={showCustomRange ? "primary" : "outline"}
            size="sm"
            onClick={() => setShowCustomRange(!showCustomRange)}
            className="text-xs"
          >
            Custom Range
          </Button>
        </div>
      </div>

      {showCustomRange && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor="start-date" className="text-sm text-gray-600 dark:text-gray-400">
                From:
              </label>
              <input
                id="start-date"
                type="date"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            
            <div className="flex items-center gap-2">
              <label htmlFor="end-date" className="text-sm text-gray-600 dark:text-gray-400">
                To:
              </label>
              <input
                id="end-date"
                type="date"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            
            <Button size="sm" onClick={handleCustomRangeSubmit}>
              Apply
            </Button>
          </div>
        </div>
      )}

      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        Current range: {getCurrentRangeLabel()}
      </div>
    </div>
  );
}