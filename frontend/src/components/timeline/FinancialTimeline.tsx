import React, { useState, useMemo } from 'react';
import { useFinancialTimeline } from '../../hooks/useTimeline';
import { TimelineItem } from './TimelineItem';
import { AnnotationForm } from './AnnotationForm';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { Alert } from '../ui/Alert';

interface FinancialTimelineProps {
  startDate: string;
  endDate: string;
  className?: string;
}

export function FinancialTimeline({ startDate, endDate, className = '' }: FinancialTimelineProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string>('');

  const {
    data: timelineData,
    isLoading,
    error,
    refetch,
  } = useFinancialTimeline(startDate, endDate);

  const handleAddAnnotation = (date?: string) => {
    setSelectedDate(date || new Date().toISOString().split('T')[0]);
    setShowAddForm(true);
  };

  const timelineStats = useMemo(() => {
    if (!timelineData?.events) return null;

    const stats = timelineData.events.reduce((acc, event) => {
      acc[event.type] = (acc[event.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return stats;
  }, [timelineData?.events]);

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={className}>
        <Alert
          type="error"
          title="Failed to load timeline"
          message="There was an error loading your financial timeline. Please try again."
          action={
            <Button onClick={() => refetch()} size="sm">
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  if (!timelineData?.events?.length) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <div className="mb-6">
          <div className="w-24 h-24 mx-auto bg-[hsl(var(--border)/0.35)] rounded-full flex items-center justify-center mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No timeline events found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            No events found for the selected date range. Start by adding your first timeline annotation!
          </p>
          <Button onClick={() => handleAddAnnotation()}>
            Add Your First Event
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header with stats and actions */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Financial Timeline
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              {timelineData.total_count} events from {new Date(startDate).toLocaleDateString()} to {new Date(endDate).toLocaleDateString()}
            </p>
          </div>
          <Button onClick={() => handleAddAnnotation()}>
            Add Event
          </Button>
        </div>

        {/* Timeline stats */}
        {timelineStats && (
          <div className="flex gap-4 flex-wrap">
            {Object.entries(timelineStats).map(([type, count]) => {
              const typeLabels: Record<string, { label: string; color: string }> = {
                annotation: { label: 'Personal Notes', color: 'bg-indigo-500/10 text-indigo-400' },
                goal_created: { label: 'Goals Started', color: 'bg-green-500/10 text-green-400' },
                goal_completed: { label: 'Goals Achieved', color: 'bg-yellow-500/10 text-yellow-400' },
                significant_transaction: { label: 'Large Transactions', color: 'bg-blue-500/10 text-blue-400' },
              };

              const typeInfo = typeLabels[type] || { label: type, icon: '📌', color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200' };

              return (
                <div
                  key={type}
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${typeInfo.color}`}
                >
                  <span>{count} {typeInfo.label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Timeline items */}
      <div className="space-y-0">
        {timelineData.events.map((event, index) => (
          <TimelineItem
            key={`${event.type}-${event.id}`}
            event={event}
            isLast={index === timelineData.events.length - 1}
          />
        ))}
      </div>

      {/* Add annotation form */}
      <AnnotationForm
        isOpen={showAddForm}
        onClose={() => setShowAddForm(false)}
        initialDate={selectedDate}
      />
    </div>
  );
}