import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { AuthState, User, LoginCredentials, RegisterCredentials, AuthResponse } from '../types/auth';
import { apiClient } from '../services/api';
import { secureStorage } from '../services/secureStorage';
import { csrfService } from '../services/csrf';

interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  checkTokenExpiration: () => Promise<void>;
  // REMOVED: initializeFromCookies - Using Supabase-only authentication
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginCredentials) => {
        try {
          set({ isLoading: true, error: null });
          
          const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
          
          // Simplified validation (no token type checking)
          if (!response || !response.accessToken || !response.refreshToken || !response.user) {
            throw new Error('Invalid authentication response structure');
          }
          
          // Store tokens securely
          apiClient.setAuthTokens(response.accessToken, response.refreshToken, response.expiresIn);
          
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          });
          throw error;
        }
      },

      register: async (credentials: RegisterCredentials) => {
        try {
          set({ isLoading: true, error: null });
          
          const response = await apiClient.post<AuthResponse>('/auth/register', credentials);
          
          // Store tokens securely
          apiClient.setAuthTokens(response.accessToken, response.refreshToken);
          
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Registration failed',
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        // Clear tokens securely
        apiClient.removeAuthTokens();
        // Clear CSRF token
        csrfService.clearToken();
        
        // Reset state
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      refreshToken: async () => {
        try {
          const refreshToken = apiClient.getRefreshToken();
          if (!refreshToken) {
            throw new Error('No refresh token available');
          }

          const response = await apiClient.post<AuthResponse>('/auth/refresh', {
            refresh_token: refreshToken,
          });

          // Simplified validation (no dual token type handling)
          if (!response || !response.accessToken || !response.refreshToken) {
            throw new Error('Invalid refresh response structure');
          }

          // Update tokens securely
          apiClient.setAuthTokens(response.accessToken, response.refreshToken, response.expiresIn);

          // Update user data if provided in refresh response
          const currentState = get();
          set({
            user: response.user || currentState.user,
            isAuthenticated: true,
            error: null,
          });
        } catch (error) {
          // If refresh fails, logout the user
          console.error('Token refresh failed:', error);
          get().logout();
          throw error;
        }
      },

      updateUser: (userUpdates: Partial<User>) => {
        const currentUser = get().user;
        if (currentUser) {
          set({
            user: { ...currentUser, ...userUpdates },
          });
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      checkTokenExpiration: async () => {
        const { isAuthenticated } = get();
        if (!isAuthenticated) return;

        // Check if tokens are expired
        if (secureStorage.areTokensExpired()) {
          try {
            await get().refreshToken();
          } catch {
            // If refresh fails, logout the user
            get().logout();
          }
        }
      },

      // REMOVED: initializeFromCookies() - Using Supabase-only authentication
      // Magic link cookie initialization no longer needed
    }),
    {
      name: 'auth-store',
      storage: createJSONStorage(() => localStorage),
      // Only persist user data and auth status, not loading states or errors
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selector hooks for better performance
export const useAuthUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);