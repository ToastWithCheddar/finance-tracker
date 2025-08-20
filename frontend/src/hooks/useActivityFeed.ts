import React from 'react';
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { activityService } from '../services/activityService';
import { userService } from '../services/userService';
import { useRealtimeActivities } from '../stores/realtimeStore';
import type { ActivityEvent, ActivityFeedOptions, ActivityResponse } from '../types/activity';

interface UseActivityFeedResult {
  activities: ActivityEvent[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
  hasMore: boolean;
  totalCount: number;
}

/**
 * Hook for fetching user activity feed data
 */
export function useActivityFeed(options: ActivityFeedOptions = {}): UseActivityFeedResult {
  const defaultOptions: ActivityFeedOptions = {
    limit: 50,
    ...options,
  };

  const {
    data,
    isLoading,
    error,
    refetch,
  }: UseQueryResult<ActivityResponse, Error> = useQuery({
    queryKey: ['activity-feed', defaultOptions],
    queryFn: async () => {
      try {
        // Try the dedicated activity endpoint first
        return await userService.getActivityFeed(defaultOptions);
      } catch (error: any) {
        // If activity endpoint doesn't exist yet, fall back to audit logs
        if (error.status === 404) {
          console.log('Activity endpoint not found, falling back to audit logs');
          const activities = await activityService.getAuditBasedActivities(defaultOptions);
          return {
            activities,
            total_count: activities.length,
            has_more: activities.length === (defaultOptions.limit || 50),
          };
        }
        throw error;
      }
    },
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute for fresh data
    refetchOnWindowFocus: true,
    retry: (failureCount, error: any) => {
      // Don't retry if it's a 404 (endpoint not implemented)
      if (error?.status === 404) {
        return false;
      }
      return failureCount < 3;
    },
  });

  return {
    activities: data?.activities || [],
    isLoading,
    error,
    refetch,
    hasMore: data?.has_more || false,
    totalCount: data?.total_count || 0,
  };
}

/**
 * Hook for fetching activity feed with real-time updates
 */
export function useRealtimeActivityFeed(options: ActivityFeedOptions = {}): UseActivityFeedResult {
  const defaultOptions: ActivityFeedOptions = {
    limit: 50,
    ...options,
  };

  // Use the base hook
  const baseResult = useActivityFeed(defaultOptions);
  
  // Get real-time activities from the store
  const realtimeActivities = useRealtimeActivities();
  
  // Merge historical and real-time activities, avoiding duplicates
  const mergedActivities = React.useMemo(() => {
    const historicalIds = new Set(baseResult.activities.map(a => a.id));
    const filteredRealtimeActivities = realtimeActivities.filter(a => !historicalIds.has(a.id));
    
    return [...filteredRealtimeActivities, ...baseResult.activities]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, defaultOptions.limit || 50);
  }, [baseResult.activities, realtimeActivities, defaultOptions.limit]);
  
  return {
    ...baseResult,
    activities: mergedActivities,
    totalCount: baseResult.totalCount + realtimeActivities.length,
  };
}