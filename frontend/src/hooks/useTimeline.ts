import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { timelineService } from '../services/timelineService';
import type { 
  TimelineAnnotationCreate, 
  TimelineAnnotationUpdate,
  TimelineFilters 
} from '../services/timelineService';

// Query keys
export const timelineKeys = {
  all: ['timeline'] as const,
  annotations: () => [...timelineKeys.all, 'annotations'] as const,
  annotationsList: (filters: TimelineFilters) => [...timelineKeys.annotations(), 'list', filters] as const,
  annotation: (id: string) => [...timelineKeys.annotations(), 'detail', id] as const,
  timeline: () => [...timelineKeys.all, 'events'] as const,
  timelineRange: (startDate: string, endDate: string) => [...timelineKeys.timeline(), startDate, endDate] as const,
};

// Timeline Events Hook
export function useFinancialTimeline(startDate: string, endDate: string) {
  return useQuery({
    queryKey: timelineKeys.timelineRange(startDate, endDate),
    queryFn: () => timelineService.getFinancialTimeline(startDate, endDate),
    enabled: Boolean(startDate && endDate),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

// Timeline Annotations Hooks
export function useTimelineAnnotations(filters?: TimelineFilters) {
  return useQuery({
    queryKey: timelineKeys.annotationsList(filters || {}),
    queryFn: () => timelineService.getAnnotations(filters),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

export function useTimelineAnnotation(id: string) {
  return useQuery({
    queryKey: timelineKeys.annotation(id),
    queryFn: () => timelineService.getAnnotation(id),
    enabled: Boolean(id),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// Mutation Hooks
export function useCreateAnnotation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TimelineAnnotationCreate) => timelineService.createAnnotation(data),
    onSuccess: () => {
      // Invalidate and refetch timeline annotations
      queryClient.invalidateQueries({ queryKey: timelineKeys.annotations() });
      
      // Invalidate timeline events that might include this date range
      queryClient.invalidateQueries({ queryKey: timelineKeys.timeline() });
      
      toast.success('Timeline annotation created successfully!');
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to create timeline annotation';
      toast.error(message);
    },
  });
}

export function useUpdateAnnotation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TimelineAnnotationUpdate }) => 
      timelineService.updateAnnotation(id, data),
    onSuccess: (updatedAnnotation, { id }) => {
      // Update the specific annotation in cache
      queryClient.setQueryData(
        timelineKeys.annotation(id),
        updatedAnnotation
      );

      // Invalidate annotations list to refresh with updated data
      queryClient.invalidateQueries({ queryKey: timelineKeys.annotations() });
      
      // Invalidate timeline events
      queryClient.invalidateQueries({ queryKey: timelineKeys.timeline() });
      
      toast.success('Timeline annotation updated successfully!');
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to update timeline annotation';
      toast.error(message);
    },
  });
}

export function useDeleteAnnotation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => timelineService.deleteAnnotation(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: timelineKeys.annotation(id) });
      
      // Invalidate annotations list
      queryClient.invalidateQueries({ queryKey: timelineKeys.annotations() });
      
      // Invalidate timeline events
      queryClient.invalidateQueries({ queryKey: timelineKeys.timeline() });
      
      toast.success('Timeline annotation deleted successfully!');
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to delete timeline annotation';
      toast.error(message);
    },
  });
}

// Utility hooks and helpers
export function useTimelineEventIcon(eventType: string): string {
  const iconMap: Record<string, string> = {
    annotation: '📝',
    goal_created: '🎯',
    goal_completed: '🏆',
    significant_transaction: '💰',
    budget_alert: '⚠️',
    milestone: '🎉',
  };
  
  return iconMap[eventType] || '📌';
}

export function useTimelineEventColor(eventType: string): string {
  const colorMap: Record<string, string> = {
    annotation: '#6366f1',
    goal_created: '#10b981',
    goal_completed: '#f59e0b',
    significant_transaction: '#3b82f6',
    budget_alert: '#ef4444',
    milestone: '#8b5cf6',
  };
  
  return colorMap[eventType] || '#6b7280';
}

export function formatTimelineDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function formatTimelineRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}