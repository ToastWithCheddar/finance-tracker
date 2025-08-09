export interface User {
  id: string;
  email: string;
  displayName?: string;
  avatarUrl?: string;
  locale?: string;
  timezone?: string;
  currency?: string;
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  [key: string]: unknown;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  displayName?: string;
  [key: string]: unknown;
}

export interface AuthResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresIn?: number;
  // REMOVED: tokenType - Using Supabase-only authentication
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  newPassword: string;
}