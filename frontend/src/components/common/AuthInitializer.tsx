import { useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { useAuthCacheManagement } from '../../hooks/useAuthCacheManagement';

/**
 * Component that initializes authentication state on app startup.
 * This handles token validation and manages React Query cache to prevent 
 * stale data across user sessions.
 */
import { logger } from '../../utils/logger';
export function AuthInitializer() {
  const checkTokenExpiration = useAuthStore((state) => state.checkTokenExpiration);
  
  // Initialize cache management for user state changes
  useAuthCacheManagement();

  useEffect(() => {
    // Check stored token validity on app startup
    logger.info('🔑 AuthInitializer: Checking stored tokens...');
    checkTokenExpiration();
    logger.info('🔑 AuthInitializer: Token validation completed');
  }, [checkTokenExpiration]);

  return null; // This component doesn't render anything
}