import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthUser } from '../stores/authStore';

/**
 * Hook to manage React Query cache when user authentication state changes
 * Clears stale cached data when switching between users or logging out
 */
import { logger } from '../utils/logger';
export function useAuthCacheManagement() {
  const queryClient = useQueryClient();
  const user = useAuthUser();
  const previousUserIdRef = useRef<string | null>(null);

  useEffect(() => {
    const currentUserId = user?.id || null;
    const previousUserId = previousUserIdRef.current;

    // If user changed (login, logout, or user switch)
    if (previousUserId !== currentUserId) {
      logger.info('[Auth Cache] User changed:', { previousUserId, currentUserId });
      
      // Clear all cached queries to prevent stale data
      queryClient.clear();
      
      // Update the ref for next comparison
      previousUserIdRef.current = currentUserId;
    }
  }, [user?.id, queryClient]);

  // Provide manual cache clearing function
  const clearUserCache = () => {
    logger.info('[Auth Cache] Manually clearing cache for user:', user?.id);
    queryClient.clear();
  };

  return { clearUserCache };
}