import { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Button } from './Button';
import { Shield, ShieldCheck } from 'lucide-react';
import type { AuthResponse } from '../../types/auth';

/**
 * DEVELOPMENT ONLY: Admin bypass for testing without full auth setup
 * This should be disabled in production!
 */
export function AdminBypassButton() {
  const [bypassing, setBypassing] = useState(false);
  const { isAuthenticated } = useAuthStore();
  
  // Only show in development
  if (import.meta.env.PROD) {
    return null;
  }

  const handleBypass = async () => {
    try {
      setBypassing(true);
      
      // Create a mock auth response for development using the working dev token
      const mockAuthResponse: AuthResponse = {
        user: {
          id: 'eadc6056-0799-423c-9bf9-6c1c4c811231',
          email: 'dev@example.com',
          displayName: 'Development User',
          avatarUrl: null,
          locale: 'en-US',
          timezone: 'UTC',
          currency: 'USD',
          createdAt: '2025-08-07T13:26:03.139796Z',
          updatedAt: '2025-08-07T13:26:03.139796Z',
          isActive: true,
        },
        accessToken: 'dev-mock-token-12345',
        refreshToken: 'dev-mock-refresh-12345',
        expiresIn: 15 * 60,
        // REMOVED: tokenType - Using Supabase-only authentication
      };
      
      // Set tokens in storage directly (bypass API call)
      const { apiClient } = await import('../../services/api');
      apiClient.setAuthTokens(mockAuthResponse.accessToken, mockAuthResponse.refreshToken);
      
      // Update auth store
      useAuthStore.setState({
        user: mockAuthResponse.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      
      console.log('🔓 Development auth bypass activated');
      
    } catch (error) {
      console.error('Failed to bypass auth:', error);
    } finally {
      setBypassing(false);
    }
  };

  if (isAuthenticated) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="flex items-center gap-2 bg-green-100 text-green-800 px-3 py-2 rounded-lg text-sm border border-green-200">
          <ShieldCheck className="h-4 w-4" />
          <span>Dev Auth Active</span>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <Button
        onClick={handleBypass}
        disabled={bypassing}
        variant="outline"
        size="sm"
        className="bg-yellow-50 border-yellow-300 text-yellow-800 hover:bg-yellow-100"
      >
        <Shield className="h-4 w-4 mr-2" />
        {bypassing ? 'Bypassing...' : 'Dev Auth Bypass'}
      </Button>
    </div>
  );
}