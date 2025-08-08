import type {
  HttpMethod,
  RequestOptions,
  PaginationParams,
  PaginatedResponse,
} from '../types/api';

/**
 * Interface for error data returned by API
 */
interface ApiErrorData {
  error?: {
    code?: string;
    message?: string;
    field?: string;
    details?: {
      value?: unknown;
      constraint?: string;
      rule?: string;
      component?: string;
      [key: string]: unknown;
    };
    requestId?: string;
  };
  message?: string;
  detail?: string;
  field?: string;
  details?: {
    value?: unknown;
    constraint?: string;
    rule?: string;
    component?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}
import type {
  ApiError,
  NetworkError,
  ValidationError,
  AuthError,
  BusinessError,
  SystemError
} from '../types/errors';
import { ErrorCodes } from '../types';
import { secureStorage } from './secureStorage';
import { csrfService } from './csrf';
import { envValidator } from '../utils/envValidation';
import { mockApiClient } from './mockApiClient';

class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;
  private useMockData: boolean;
  private uiOnlyMode: boolean;

  constructor(baseURL?: string) {
    const config = envValidator.getConfig();
    this.baseURL = (baseURL || config.VITE_API_URL).replace(/\/$/, ''); // Remove trailing slash
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
    
    // Check if we should use mock data
    this.useMockData = import.meta.env.VITE_USE_MOCK_DATA === 'true';
    this.uiOnlyMode = import.meta.env.VITE_UI_ONLY_MODE === 'true';
    
    if (this.useMockData || this.uiOnlyMode) {
      console.log('🎭 API Client using mock data for UI development');
    }
  }

  private getAuthToken(): string | null {
    return secureStorage.getAccessToken();
  }

  private getHeaders(customHeaders?: Record<string, string>): Record<string, string> {
    const headers = { 
      ...this.defaultHeaders, 
      ...csrfService.getHeaders(), // Add CSRF protection
      ...customHeaders 
    };
    
    const token = this.getAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
      // Debug logging for first few characters
      console.log('🔐 API Request with token:', token.substring(0, 20) + '...');
    } else {
      console.log('🚫 API Request without token');
    }

    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await this.createStructuredError(response);
      throw error;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }

    return response.text() as unknown as T;
  }

  private async createStructuredError(response: Response): Promise<ApiError> {
    const timestamp = new Date().toISOString();
    const statusCode = response.status;
    
    let errorData: ApiErrorData = {};
    try {
      errorData = await response.json() as ApiErrorData;
    } catch {
      // If we can't parse JSON, create generic error
    }

    // Extract error information
    const code = errorData.error?.code || this.getErrorCodeFromStatus(statusCode);
    const message = errorData.error?.message || errorData.message || errorData.detail || response.statusText;
    const field = errorData.error?.field || errorData.field;
    const details = errorData.error?.details || errorData.details;
    const requestId = response.headers.get('x-request-id') || errorData.error?.requestId;

    // Create appropriate error type based on status code
    switch (statusCode) {
      case 400:
        return {
          code,
          message,
          timestamp,
          requestId,
          field,
          details,
          value: details?.value,
          constraint: details?.constraint
        } as ValidationError;

      case 401:
        return {
          code,
          message,
          timestamp,
          requestId,
          authType: 'authentication',
          details
        } as AuthError;

      case 403:
        return {
          code,
          message,
          timestamp,
          requestId,
          authType: 'authorization',
          details
        } as AuthError;

      case 422:
        return {
          code,
          message,
          timestamp,
          requestId,
          businessRule: details?.rule || 'validation_failed',
          context: details,
          details
        } as BusinessError;

      case 500:
      case 502:
      case 503:
      case 504:
        return {
          code,
          message,
          timestamp,
          requestId,
          systemComponent: details?.component || 'api',
          severity: statusCode >= 500 ? 'critical' : 'high',
          details
        } as SystemError;

      default:
        // Network or other errors
        return {
          code,
          message,
          timestamp,
          requestId,
          statusCode,
          retryable: this.isRetryableStatus(statusCode),
          retryAfter: this.getRetryAfter(response),
          details
        } as NetworkError;
    }
  }

  private getErrorCodeFromStatus(statusCode: number): string {
    switch (statusCode) {
      case 400: return ErrorCodes.VALIDATION_FAILED;
      case 401: return ErrorCodes.UNAUTHORIZED;
      case 403: return ErrorCodes.FORBIDDEN;
      case 422: return ErrorCodes.VALIDATION_FAILED;
      case 500: return ErrorCodes.INTERNAL_SERVER_ERROR;
      case 502: return ErrorCodes.SERVICE_UNAVAILABLE;
      case 503: return ErrorCodes.SERVICE_UNAVAILABLE;
      case 504: return ErrorCodes.TIMEOUT;
      default: return ErrorCodes.NETWORK_ERROR;
    }
  }

  private isRetryableStatus(statusCode: number): boolean {
    return [408, 429, 500, 502, 503, 504].includes(statusCode);
  }

  private getRetryAfter(response: Response): number | undefined {
    const retryAfter = response.headers.get('retry-after');
    return retryAfter ? parseInt(retryAfter, 10) * 1000 : undefined;
  }

  private buildURL(endpoint: string, params?: Record<string, string | number | boolean> | PaginationParams): string {
    const url = new URL(`${this.baseURL}${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  async request<T>(
    method: HttpMethod,
    endpoint: string,
    data?: Record<string, unknown>,
    options?: RequestOptions
  ): Promise<T> {
    // Use mock API client if in mock mode
    if (this.useMockData || this.uiOnlyMode) {
      return mockApiClient.request<T>(endpoint, {
        method,
        body: data ? JSON.stringify(data) : undefined,
        headers: this.getHeaders(options?.headers)
      });
    }
    
    let retried = false;

    while (true) {
      const url = this.buildURL(endpoint, options?.params);
      const headers = this.getHeaders(options?.headers);

      const config: RequestInit = {
        method,
        headers,
        credentials: 'include', // Send cookies with requests
        signal: options?.timeout ? AbortSignal.timeout(options.timeout) : undefined,
      };

      if (data && method !== 'GET') {
        config.body = JSON.stringify(data);
      }

      try {
        const response = await fetch(url, config);

        // If not 401 or already retried or no refresh token available, handle normally
        if (response.status !== 401 || retried || !secureStorage.getRefreshToken()) {
          return this.handleResponse<T>(response);
        }

        // One-shot silent refresh attempt
        retried = true;
        console.log('🔄 Attempting silent token refresh...');
        
        try {
          const refreshResponse = await fetch(`${this.baseURL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ 
              refresh_token: secureStorage.getRefreshToken() 
            }),
          });

          if (!refreshResponse.ok) {
            console.warn('🚨 Token refresh failed with status:', refreshResponse.status);
            secureStorage.clearTokens();
            return this.handleResponse<T>(response);
          }

          let refreshData;
          try {
            refreshData = await refreshResponse.json();
          } catch (parseError) {
            console.error('❌ Failed to parse refresh response JSON:', parseError);
            secureStorage.clearTokens();
            return this.handleResponse<T>(response);
          }

          // Validate refresh response structure
          if (!refreshData || !refreshData.accessToken || !refreshData.refreshToken) {
            console.error('❌ Invalid refresh response structure:', refreshData);
            secureStorage.clearTokens();
            return this.handleResponse<T>(response);
          }

          const { accessToken, refreshToken, expiresIn } = refreshData;
          this.setAuthTokens(accessToken, refreshToken, expiresIn);
          console.log('✅ Token refresh successful');

          // Update the authorization header for retry
          config.headers = {
            ...config.headers as Record<string, string>,
            Authorization: `Bearer ${accessToken}`
          };

          // Continue loop to retry the original request with new token
          continue;
        } catch (refreshError) {
          console.error('❌ Token refresh error:', refreshError);
          // Clear tokens and bubble up original 401
          secureStorage.clearTokens();
          return this.handleResponse<T>(response);
        }
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error('An unexpected error occurred');
      }
    }
  }

  // Convenience methods
  async get<T>(endpoint: string, params?: Record<string, string | number | boolean> | PaginationParams, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, { ...options, params });
  }

  async post<T>(endpoint: string, data?: Record<string, unknown>, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, data, options);
  }

  async put<T>(endpoint: string, data?: Record<string, unknown>, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', endpoint, data, options);
  }

  async patch<T>(endpoint: string, data?: Record<string, unknown>, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, options);
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options);
  }

  // Paginated requests
  async getPaginated<T>(
    endpoint: string,
    params?: PaginationParams,
    options?: RequestOptions
  ): Promise<PaginatedResponse<T>> {
    return this.get<PaginatedResponse<T>>(endpoint, params, options);
  }

  // File upload with FormData
  async postFormData<T>(endpoint: string, formData: FormData, options?: RequestOptions): Promise<T> {
    const url = this.buildURL(endpoint, options?.params);
    const headers = this.getHeaders(options?.headers);
    
    // Remove Content-Type header to let browser set it automatically for FormData
    delete headers['Content-Type'];

    const config: RequestInit = {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include', // Send cookies with FormData requests
      signal: options?.timeout ? AbortSignal.timeout(options.timeout) : undefined,
    };

    try {
      const response = await fetch(url, config);
      return this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('An unexpected error occurred');
    }
  }

  // Binary data download
  async getBlob(endpoint: string, params?: Record<string, any>, options?: RequestOptions): Promise<Blob> {
    const url = this.buildURL(endpoint, params);
    const headers = this.getHeaders(options?.headers);

    const config: RequestInit = {
      method: 'GET',
      headers,
      credentials: 'include', // Send cookies with blob requests
      signal: options?.timeout ? AbortSignal.timeout(options.timeout) : undefined,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await this.createStructuredError(response);
        throw error;
      }

      return response.blob();
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('An unexpected error occurred');
    }
  }

  // Auth token management
  setAuthTokens(accessToken: string, refreshToken: string, expiresIn?: number): void {
    secureStorage.setTokens(accessToken, refreshToken, expiresIn);
  }

  removeAuthTokens(): void {
    secureStorage.clearTokens();
  }

  hasAuthToken(): boolean {
    return secureStorage.hasValidTokens();
  }

  getRefreshToken(): string | null {
    return secureStorage.getRefreshToken();
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();

// Export the class for testing or creating custom instances
export { ApiClient };