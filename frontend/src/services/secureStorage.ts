/**
 * Secure token storage service
 * Uses httpOnly cookies when possible, falls back to sessionStorage
 */

class SecureStorage {
  private readonly ACCESS_TOKEN_KEY = 'finance_access_token';
  private readonly REFRESH_TOKEN_KEY = 'finance_refresh_token';
  private readonly EXPIRES_AT_KEY = 'finance_token_expires';

  /**
   * Store authentication tokens securely
   */
  setTokens(accessToken: string, refreshToken: string, expiresIn?: number): void {
    try {
      const expiresAt = expiresIn ? Date.now() + (expiresIn * 1000) : Date.now() + (30 * 60 * 1000); // 30 min default

      // Use sessionStorage instead of localStorage for better security
      // sessionStorage is cleared when the tab is closed
      sessionStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
      sessionStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
      sessionStorage.setItem(this.EXPIRES_AT_KEY, expiresAt.toString());

      // Clear any old localStorage tokens for migration
      this.clearLegacyTokens();
    } catch (error) {
      console.error('Failed to store tokens:', error);
      throw new Error('Token storage failed');
    }
  }

  /**
   * Get tokens from cookies (for magic link authentication)
   */
  private getCookieToken(name: string): string | null {
    if (typeof document === 'undefined') return null;
    
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      const cookieValue = parts.pop()?.split(';').shift();
      return cookieValue || null;
    }
    return null;
  }

  /**
   * Initialize tokens from cookies if available (for magic link flow)
   */
  initializeFromCookies(): boolean {
    console.log('🍪 Checking for auth cookies...');
    const accessToken = this.getCookieToken('access_token');
    const refreshToken = this.getCookieToken('refresh_token');
    
    console.log('🍪 Found cookies:', { 
      hasAccessToken: !!accessToken, 
      hasRefreshToken: !!refreshToken,
      accessTokenLength: accessToken?.length || 0
    });
    
    if (accessToken && refreshToken) {
      console.log('🍪 Initializing tokens from cookies');
      this.setTokens(accessToken, refreshToken);
      return true;
    }
    console.log('🍪 No valid cookies found');
    return false;
  }

  /**
   * Get access token
   */
  getAccessToken(): string | null {
    try {
      const token = sessionStorage.getItem(this.ACCESS_TOKEN_KEY);
      if (!token) {
        // If no token in sessionStorage, try cookies as fallback
        return this.getCookieToken('access_token');
      }
      return token;
    } catch (error) {
      console.error('Failed to retrieve access token:', error);
      return null;
    }
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    try {
      const token = sessionStorage.getItem(this.REFRESH_TOKEN_KEY);
      if (!token) {
        // If no token in sessionStorage, try cookies as fallback
        return this.getCookieToken('refresh_token');
      }
      return token;
    } catch (error) {
      console.error('Failed to retrieve refresh token:', error);
      return null;
    }
  }

  /**
   * Check if tokens are expired
   */
  areTokensExpired(): boolean {
    try {
      const expiresAt = sessionStorage.getItem(this.EXPIRES_AT_KEY);
      if (!expiresAt) return true;
      
      return Date.now() >= parseInt(expiresAt);
    } catch (error) {
      console.error('Failed to check token expiration:', error);
      return true;
    }
  }

  /**
   * Check if we have valid tokens
   */
  hasValidTokens(): boolean {
    const accessToken = this.getAccessToken();
    const refreshToken = this.getRefreshToken();
    
    return !!(accessToken && refreshToken && !this.areTokensExpired());
  }

  /**
   * Clear all stored tokens
   */
  clearTokens(): void {
    try {
      sessionStorage.removeItem(this.ACCESS_TOKEN_KEY);
      sessionStorage.removeItem(this.REFRESH_TOKEN_KEY);
      sessionStorage.removeItem(this.EXPIRES_AT_KEY);
      
      // Also clear legacy localStorage tokens
      this.clearLegacyTokens();
    } catch (error) {
      console.error('Failed to clear tokens:', error);
    }
  }

  /**
   * Clear legacy localStorage tokens (migration helper)
   */
  private clearLegacyTokens(): void {
    try {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('admin_bypass');
    } catch (error) {
      // Ignore errors for cleanup
    }
  }

  /**
   * Get token data for debugging (development only)
   */
  getTokenInfo(): { hasTokens: boolean; expiresAt: string | null; isExpired: boolean } {
    if (import.meta.env.PROD) {
      return { hasTokens: false, expiresAt: null, isExpired: true };
    }

    const expiresAt = sessionStorage.getItem(this.EXPIRES_AT_KEY);
    return {
      hasTokens: !!(this.getAccessToken() && this.getRefreshToken()),
      expiresAt: expiresAt ? new Date(parseInt(expiresAt)).toISOString() : null,
      isExpired: this.areTokensExpired(),
    };
  }
}

// Export singleton instance
export const secureStorage = new SecureStorage();