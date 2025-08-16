import React, { useState } from 'react';
import { FinancialTimeline } from '../components/timeline/FinancialTimeline';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

export function Timeline() {
  // Default to last 6 months
  const [dateRange, setDateRange] = useState(() => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 6);
    
    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    };
  });

  const [tempDateRange, setTempDateRange] = useState(dateRange);

  const handleDateRangeUpdate = () => {
    // Validate date range
    if (tempDateRange.startDate > tempDateRange.endDate) {
      alert('Start date must be before end date');
      return;
    }

    // Validate date range isn't too large (max 2 years)
    const startDate = new Date(tempDateRange.startDate);
    const endDate = new Date(tempDateRange.endDate);
    const diffDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays > 730) {
      alert('Date range cannot exceed 2 years');
      return;
    }

    setDateRange(tempDateRange);
  };

  const handleQuickDateRange = (months: number) => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - months);
    
    const newRange = {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    };
    
    setTempDateRange(newRange);
    setDateRange(newRange);
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'hsl(var(--bg))' }}>
      <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="mb-8 glass-surface p-6">
          <h1 className="text-3xl font-bold mb-2">
            Financial Timeline
          </h1>
          <p className="text-lg text-[hsl(var(--text))/0.7]">
            View your financial journey with important events, goals, and milestones
          </p>
        </div>

        {/* Date Range Filters */}
        <div className="glass-surface p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4">
            Timeline Period
          </h3>
          
          {/* Quick Range Buttons */}
          <div className="flex gap-2 mb-4 flex-wrap">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickDateRange(1)}
            >
              Last Month
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickDateRange(3)}
            >
              Last 3 Months
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickDateRange(6)}
            >
              Last 6 Months
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickDateRange(12)}
            >
              Last Year
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickDateRange(24)}
            >
              Last 2 Years
            </Button>
          </div>

          {/* Custom Date Range */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label htmlFor="startDate" className="block text-sm font-medium mb-1">
                Start Date
              </label>
              <Input
                id="startDate"
                type="date"
                value={tempDateRange.startDate}
                onChange={(e) => setTempDateRange(prev => ({ ...prev, startDate: e.target.value }))}
              />
            </div>
            
            <div>
              <label htmlFor="endDate" className="block text-sm font-medium mb-1">
                End Date
              </label>
              <Input
                id="endDate"
                type="date"
                value={tempDateRange.endDate}
                onChange={(e) => setTempDateRange(prev => ({ ...prev, endDate: e.target.value }))}
              />
            </div>
            
            <div>
              <Button
                onClick={handleDateRangeUpdate}
                disabled={dateRange.startDate === tempDateRange.startDate && dateRange.endDate === tempDateRange.endDate}
                className="w-full"
              >
                Update Timeline
              </Button>
            </div>
          </div>

          {/* Date Range Info */}
          <div className="mt-4 text-sm text-[hsl(var(--text))/0.6]">
            <p>
              Showing timeline from {new Date(dateRange.startDate).toLocaleDateString()} to {new Date(dateRange.endDate).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Timeline Content */}
        <FinancialTimeline
          startDate={dateRange.startDate}
          endDate={dateRange.endDate}
          className="glass-surface p-6"
        />

        {/* Help Section */}
        <div className="mt-8 rounded-lg p-6 border border-blue-500/30 bg-blue-500/10">
          <h3 className="text-lg font-semibold text-blue-400 mb-2">
            About Your Financial Timeline
          </h3>
          <div className="text-blue-300 space-y-2">
            <p>
              Your financial timeline combines important events from across your financial life:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li><strong>Personal Notes:</strong> Events you add manually (job changes, life events, etc.)</li>
              <li><strong>Goal Milestones:</strong> When you start or complete financial goals</li>
              <li><strong>Large Transactions:</strong> Significant income or expenses over $500</li>
              <li><strong>Budget Alerts:</strong> When you approach or exceed budget limits</li>
            </ul>
            <p className="mt-3">
              Use the "Add Event" button to create personal annotations that give context to your financial data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}