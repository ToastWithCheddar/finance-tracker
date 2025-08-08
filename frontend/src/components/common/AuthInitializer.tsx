import { useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { useAuthCacheManagement } from '../../hooks/useAuthCacheManagement';

/**
 * Component that initializes authentication state on app startup.
 * This handles magic link authentication by checking for cookies
 * and manages React Query cache to prevent stale data across user sessions.
 */
export function AuthInitializer() {
  const initializeFromCookies = useAuthStore((state) => state.initializeFromCookies);
  
  // Initialize cache management for user state changes
  useAuthCacheManagement();

  useEffect(() => {
    // Check for magic link cookies on app startup
    console.log('🔑 AuthInitializer: Checking for cookies...');
    const initialized = initializeFromCookies();
    console.log('🔑 AuthInitializer: Cookie initialization result:', initialized);
  }, [initializeFromCookies]);

  return null; // This component doesn't render anything
}