import type {
  HttpMethod,
  RequestOptions,
  PaginationParams,
  PaginatedResponse,
} from '../types/api';

/**
 * Interface for error data returned by API
 */
import { logger } from '../utils/logger';
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

class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor(baseURL?: string) {
    const config = envValidator.getConfig();
    this.baseURL = (baseURL || config.VITE_API_URL).replace(/\/$/, ''); // Remove trailing slash
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
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
    }
    // FE-SEC-004: never log Authorization tokens (not even prefixes).

    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await this.createStructuredError(response);
      throw error;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const body = await response.json();

      // Centralized envelope error parsing: detect { error: true, message, error_code }
      if (body && typeof body === 'object' && (body.error === true || body.success === false)) {
        const timestamp = new Date().toISOString();
        const statusCode = response.status;
        const code = body.error_code || body.code || this.getErrorCodeFromStatus(statusCode);
        const message = body.message || 'Request failed';

        const structuredError: NetworkError = {
          code,
          message,
          timestamp,
          requestId: response.headers.get('x-request-id') || undefined,
          statusCode,
          retryable: this.isRetryableStatus(statusCode),
          retryAfter: this.getRetryAfter(response),
          details: body.details || body.error?.details,
        } as NetworkError;
        throw structuredError;
      }

      return body as T;
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
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
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
            logger.warn('🚨 Token refresh failed with status:', refreshResponse.status);
            secureStorage.clearTokens();
            return this.handleResponse<T>(response);
          }

          let refreshData;
          try {
            refreshData = await refreshResponse.json();
          } catch (parseError) {
            secureStorage.clearTokens();
            return this.handleResponse<T>(response);
          }

          // FE-SEC-003: backend returns snake_case (FastAPI default JSON
          // shape). Reading camelCase keys produced silent token clears
          // and forced full re-logins. Read snake_case directly; keep
          // camelCase as a defensive fallback for tests/mocks.
          const accessToken: string | undefined =
            refreshData?.access_token ?? refreshData?.accessToken;
          const refreshTokenNew: string | undefined =
            refreshData?.refresh_token ?? refreshData?.refreshToken;
          const expiresIn: number | undefined =
            refreshData?.expires_in ?? refreshData?.expiresIn;

          if (!refreshData || !accessToken || !refreshTokenNew) {
            secureStorage.clearTokens();
            return this.handleResponse<T>(response);
          }

          this.setAuthTokens(accessToken, refreshTokenNew, expiresIn);

          // Update the authorization header for retry
          config.headers = {
            ...config.headers as Record<string, string>,
            Authorization: `Bearer ${accessToken!}`
          };

          // Continue loop to retry the original request with new token
          continue;
        } catch (refreshError) {
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

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, data, options);
  }

  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', endpoint, data, options);
  }

  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
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

// Legacy export for backward compatibility
export const api = apiClient;

// Export the class for testing or creating custom instances
export { ApiClient };

// ===== Helpers: list envelope normalization and snake->camel mapping =====

export interface NormalizedList<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export function normalizeListEnvelope<T = any>(res: any): NormalizedList<T> {
  // Determine items array
  const items: T[] = Array.isArray(res)
    ? (res as T[])
    : (res?.items as T[]) || (res?.transactions as T[]) || [];

  // Determine total
  const totalRaw = typeof res?.total === 'number' ? res.total : items.length;

  // Determine per_page
  const perPage = typeof res?.limit === 'number'
    ? res.limit
    : (typeof res?.per_page === 'number' ? res.per_page : items.length);

  // Determine page
  let page = 1;
  if (typeof res?.page === 'number') {
    page = res.page;
  } else if (typeof res?.offset === 'number' && typeof res?.limit === 'number' && res.limit > 0) {
    page = Math.floor(res.offset / res.limit) + 1;
  }

  // Determine pages
  const pages = typeof res?.pages === 'number' ? res.pages : (perPage > 0 ? Math.ceil(totalRaw / perPage) : 1);

  return {
    items,
    total: totalRaw,
    page,
    per_page: perPage,
    pages,
  };
}

export function snakeToCamelShallow<T extends Record<string, any>>(obj: T): any {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return obj;
  const out: Record<string, any> = {};
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    out[camelKey] = value;
  }
  return out;
}
