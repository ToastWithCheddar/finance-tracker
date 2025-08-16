import { useState } from 'react';
import type { TimelineEvent } from '../../services/timelineService';
import { formatTimelineDate, formatTimelineRelativeTime } from '../../hooks/useTimeline';
import { Button } from '../ui/Button';
import { AnnotationForm } from './AnnotationForm';
import { useDeleteAnnotation } from '../../hooks/useTimeline';

interface TimelineItemProps {
  event: TimelineEvent;
  isLast?: boolean;
}

export function TimelineItem({ event, isLast = false }: TimelineItemProps) {
  const [showEditForm, setShowEditForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const deleteMutation = useDeleteAnnotation();

  const isUserAnnotation = event.source === 'user_annotation';
  const formattedDate = formatTimelineDate(event.date);
  const relativeTime = formatTimelineRelativeTime(event.date);

  const handleDelete = async () => {
    if (!isUserAnnotation) return;
    
    try {
      await deleteMutation.mutateAsync(event.id);
      setShowDeleteConfirm(false);
    } catch (error) {
      // Error handling is done in the mutation hook
    }
  };

  const getEventTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      annotation: 'Personal Note',
      goal_created: 'Goal Started',
      goal_completed: 'Goal Achieved',
      significant_transaction: 'Large Transaction',
      budget_alert: 'Budget Alert',
      milestone: 'Milestone',
    };
    return labels[type] || 'Event';
  };

  const formatAmount = (extraData: any) => {
    if (extraData?.amount_cents) {
      const amount = Math.abs(extraData.amount_cents) / 100;
      return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (extraData?.target_amount) {
      const amount = extraData.target_amount / 100;
      return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return null;
  };

  const annotation = isUserAnnotation ? {
    id: event.id,
    user_id: '', // Not needed for editing
    date: event.date,
    title: event.title,
    description: event.description,
    icon: event.icon,
    color: event.color,
    extra_data: event.extra_data,
    created_at: event.created_at,
  } : undefined;

  return (
    <>
      <div className="relative flex items-start space-x-4">
        {/* Timeline line */}
        {!isLast && (
          <div className="absolute left-6 top-12 w-0.5 h-full bg-gray-200 dark:bg-gray-700" />
        )}

        {/* Event icon */}
        <div
          className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold text-lg relative z-10"
          style={{ backgroundColor: event.color }}
        >
          <span>{event.icon}</span>
        </div>

        {/* Event content */}
        <div className="flex-1 min-w-0 pb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {event.title}
                  </h3>
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                    {getEventTypeLabel(event.type)}
                  </span>
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {formattedDate} • {relativeTime}
                </div>
              </div>

              {/* Actions for user annotations */}
              {isUserAnnotation && (
                <div className="flex gap-1 ml-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowEditForm(true)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    title="Edit annotation"
                  >
                    ✏️
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDeleteConfirm(true)}
                    className="text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                    title="Delete annotation"
                  >
                    🗑️
                  </Button>
                </div>
              )}
            </div>

            {/* Description */}
            {event.description && (
              <p className="text-gray-700 dark:text-gray-300 mb-3">
                {event.description}
              </p>
            )}

            {/* Amount (for financial events) */}
            {formatAmount(event.extra_data) && (
              <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                {formatAmount(event.extra_data)}
              </div>
            )}

            {/* Additional metadata */}
            {event.extra_data?.category && (
              <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Category: {event.extra_data.category}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Delete Annotation
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Are you sure you want to delete this timeline annotation? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="flex-1"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit form */}
      {showEditForm && annotation && (
        <AnnotationForm
          isOpen={showEditForm}
          onClose={() => setShowEditForm(false)}
          annotation={annotation}
        />
      )}
    </>
  );
}