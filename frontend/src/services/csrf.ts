/**
 * CSRF protection service
 * Generates and validates CSRF tokens for API requests
 */

class CSRFService {
  private csrfToken: string | null = null;
  private readonly TOKEN_KEY = 'csrf_token';
  private readonly TOKEN_HEADER = 'X-CSRF-Token';

  /**
   * Generate a new CSRF token
   */
  private generateToken(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Get or generate CSRF token
   */
  getToken(): string {
    if (!this.csrfToken) {
      this.csrfToken = this.generateToken();
      sessionStorage.setItem(this.TOKEN_KEY, this.csrfToken);
    }
    return this.csrfToken;
  }

  /**
   * Get CSRF headers for API requests
   */
  getHeaders(): Record<string, string> {
    return {
      [this.TOKEN_HEADER]: this.getToken(),
    };
  }

  /**
   * Refresh CSRF token (call on login/logout)
   */
  refreshToken(): void {
    this.csrfToken = this.generateToken();
    sessionStorage.setItem(this.TOKEN_KEY, this.csrfToken);
  }

  /**
   * Clear CSRF token
   */
  clearToken(): void {
    this.csrfToken = null;
    sessionStorage.removeItem(this.TOKEN_KEY);
  }

  /**
   * Restore token from storage (on page refresh)
   */
  restoreToken(): void {
    const stored = sessionStorage.getItem(this.TOKEN_KEY);
    if (stored) {
      this.csrfToken = stored;
    } else {
      this.refreshToken();
    }
  }
}

// Export singleton instance
export const csrfService = new CSRFService();

// Initialize on import
csrfService.restoreToken();