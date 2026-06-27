import { apiClient } from '../api';
import type { 
  ApiError, 
  ErrorRecoveryStrategy, 
  ErrorContext
} from '../../types/errors';
import type { PaginationParams, PaginatedResponse } from '../../types/api';

/**
 * Standard service response structure
 */
import { logger } from '../../utils/logger';
export interface ServiceResponse<T> {
  success: boolean;
  data: T;
  metadata?: {
    timestamp: string;
    [key: string]: unknown;
  };
}

/**
 * Standard service error structure
 */
export interface ServiceError {
  code: string;
  message: string;
  status?: number;
  details?: unknown;
}

/**
 * Union type for service operations
 */
export type ServiceResult<T> = 
  | (ServiceResponse<T> & { success: true })
  | { success: false; error: ServiceError; metadata?: { timestamp: string; [key: string]: unknown } };

/**
 * Base service class providing common functionality for all API services
 */
export abstract class BaseService {
  protected abstract baseEndpoint: string;

  // FE-PERF-005: The in-memory cache (Map<string, {data, timestamp, ttl}>),
  // along with `getCachedData` / `setCachedData` / `clearCache` and the
  // `useCache` / `cacheTtl` options, has been removed. React Query is now the
  // single source of truth for client-side caching. The `useCache`/`cacheTtl`
  // option fields are retained on method signatures purely so existing
  // callers continue to typecheck — they are now no-ops.

  /**
   * Validate response exists and is not null/undefined
   */
  private validateResponse<T>(result: T, endpoint: string): T {
    if (result === null || result === undefined) {
      throw new Error(`Empty response from ${endpoint}`);
    }
    return result;
  }

  /**
   * No-op kept for backwards compatibility with a single legacy caller
   * (`transactionService.importFromCSV`). React Query handles invalidation
   * for real now; this method is intentionally inert.
   *
   * @deprecated Use `queryClient.invalidateQueries(...)` from React Query.
   */
  protected clearCache(_key?: string): void {
    // intentional no-op — see FE-PERF-005
  }

  /**
   * Standard GET request. Always hits the network — caching is delegated to
   * React Query at the call site.
   */
  protected async get<T>(
    endpoint: string,
    params?: Record<string, any>,
    options?: {
      // Retained for back-compat; ignored. See FE-PERF-005.
      useCache?: boolean;
      cacheTtl?: number;
      context?: ErrorContext;
      wrapResponse?: boolean;
    }
  ): Promise<T> {
    const fullEndpoint = this.buildEndpoint(endpoint);

    try {
      const result = await apiClient.get<T>(fullEndpoint, params);
      return this.validateResponse(result, endpoint);
    } catch (error) {
      const enhancedError = this.handleServiceError(error as ApiError, {
        ...options?.context,
        feature: options?.context?.feature || this.constructor.name,
        action: 'GET',
        metadata: {
          ...options?.context?.metadata,
          endpoint,
          params: params ? Object.keys(params) : undefined
        }
      });
      throw enhancedError;
    }
  }

  /**
   * Standard POST request
   */
  protected async post<T>(
    endpoint: string, 
    data?: Record<string, unknown>,
    options?: { context?: ErrorContext }
  ): Promise<T> {
    try {
      const fullEndpoint = this.buildEndpoint(endpoint);
      const result = await apiClient.post<T>(fullEndpoint, data);

      return result;
    } catch (error) {
      throw this.handleServiceError(error as ApiError, options?.context);
    }
  }

  /**
   * Standard PUT request
   */
  protected async put<T>(
    endpoint: string, 
    data?: Record<string, unknown>,
    options?: { context?: ErrorContext }
  ): Promise<T> {
    try {
      const fullEndpoint = this.buildEndpoint(endpoint);
      const result = await apiClient.put<T>(fullEndpoint, data);

      return result;
    } catch (error) {
      throw this.handleServiceError(error as ApiError, options?.context);
    }
  }

  /**
   * Standard DELETE request
   */
  protected async delete<T>(
    endpoint: string,
    options?: { context?: ErrorContext }
  ): Promise<T> {
    try {
      const fullEndpoint = this.buildEndpoint(endpoint);
      const result = await apiClient.delete<T>(fullEndpoint);

      return result;
    } catch (error) {
      throw this.handleServiceError(error as ApiError, options?.context);
    }
  }

  /**
   * Paginated GET request for large datasets that are split into pages
   */
  protected async getPaginated<T>(
    endpoint: string,
    params?: PaginationParams & Record<string, any>,
    options?: { 
      useCache?: boolean; 
      cacheTtl?: number;
      context?: ErrorContext;
    }
  ): Promise<PaginatedResponse<T>> {
    // Pass raw endpoint to avoid double-prefixing; this.get will build the full path
    return this.get<PaginatedResponse<T>>(endpoint, params, options);
  }

  /**
   * Handle service-specific errors and add context
   */
  protected handleServiceError(error: ApiError, context?: ErrorContext): ApiError {
    // Add service context to error
    const enhancedError = {
      ...error,
      details: {
        ...error.details,
        service: this.constructor.name,
        endpoint: this.baseEndpoint,
        context
      }
    };

    // Log error for debugging
    this.logError(enhancedError, context);

    return enhancedError;
  }

  /**
   * Get error recovery strategy based on error type
   */
  protected getRecoveryStrategy(error: ApiError): ErrorRecoveryStrategy {
    // Network errors - usually retryable
    if ('statusCode' in error && 'retryable' in error) {
      return {
        canRetry: error.retryable,
        retryDelay: error.retryAfter || 1000,
        maxRetries: 3,
        userMessage: 'Network error occurred. Please try again.'
      };
    }

    // Auth errors - redirect to login
    if ('authType' in error) {
      return {
        canRetry: false,
        fallbackAction: () => {
          // Could trigger auth refresh or redirect
          logger.warn('Auth error - may need to refresh session');
        },
        userMessage: 'Authentication required. Please log in again.'
      };
    }

    // Validation errors - not retryable, show specific message
    if ('field' in error) {
      return {
        canRetry: false,
        userMessage: error.message
      };
    }

    // Business errors - not retryable, show specific message
    if ('businessRule' in error) {
      return {
        canRetry: false,
        userMessage: error.message
      };
    }

    // System errors - may be retryable
    if ('systemComponent' in error) {
      return {
        canRetry: error.severity !== 'critical',
        retryDelay: 5000,
        maxRetries: 2,
        userMessage: 'System error occurred. Please try again later.'
      };
    }

    // Default strategy
    return {
      canRetry: false,
      userMessage: 'An unexpected error occurred.'
    };
  }

  /**
   * Log errors for debugging and monitoring
   */
  private logError(error: ApiError, context?: ErrorContext): void {
    const logData = {
      error: {
        code: error.code,
        message: error.message,
        timestamp: error.timestamp
      },
      context,
      service: this.constructor.name,
      endpoint: this.baseEndpoint
    };

    // In development, log to console
    if (import.meta.env.DEV) {
      logger.error('Service Error:', logData);
    }

    // In production, could send to monitoring service
    // Example: monitoringService.logError(logData);
  }

  /**
   * Utility method to build endpoint URLs
   */
  protected buildEndpoint(path: string): string {
    return `${this.baseEndpoint}${path.startsWith('/') ? path : `/${path}`}`;
  }

  /**
   * Utility method for currency formatting (cents to display)
   */
  protected formatCurrency(amountCents: number, currency: string = 'USD'): string {
    const dollars = amountCents / 100;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(Math.abs(dollars));
  }

  /**
   * Utility method for converting dollars to cents
   */
  protected dollarsToCents(dollars: number): number {
    return Math.round(dollars * 100);
  }

  /**
   * Utility method for converting cents to dollars
   */
  protected centsToDollars(cents: number): number {
    return cents / 100;
  }

  /**
   * Utility method to build query parameters
   */
  protected buildParams(filters: Record<string, any>): Record<string, string> {
    const params: Record<string, string> = {};
    
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '') {
        if (typeof value === 'boolean') {
          params[key] = value.toString();
        } else if (typeof value === 'number') {
          params[key] = value.toString();
        } else if (typeof value === 'string') {
          params[key] = value;
        } else if (Array.isArray(value)) {
          params[key] = value.join(',');
        } else {
          params[key] = String(value);
        }
      }
    }
    
    return params;
  }

  /**
   * POST request with FormData for file uploads
   */
  protected async postFormData<T>(
    endpoint: string,
    formData: FormData,
    options?: { context?: ErrorContext }
  ): Promise<T> {
    try {
      const fullEndpoint = this.buildEndpoint(endpoint);
      const result = await apiClient.postFormData<T>(fullEndpoint, formData);

      return result;
    } catch (error) {
      throw this.handleServiceError(error as ApiError, options?.context);
    }
  }

  /**
   * GET request that returns a Blob (for file downloads)
   */
  protected async getBlob(
    endpoint: string,
    params?: Record<string, any>,
    options?: { context?: ErrorContext }
  ): Promise<ServiceResponse<Blob>> {
    try {
      const fullEndpoint = this.buildEndpoint(endpoint);
      const result = await apiClient.getBlob(fullEndpoint, params);
      
      return {
        success: true,
        data: result,
        metadata: {
          timestamp: new Date().toISOString()
        }
      };
    } catch (error) {
      throw this.handleServiceError(error as ApiError, options?.context);
    }
  }
  /**
   * Wrapped GET request that returns ServiceResponse<T>
   */
  protected async getWithWrapper<T>(
    endpoint: string, 
    params?: Record<string, any>,
    options?: { 
      useCache?: boolean; 
      cacheTtl?: number;
      context?: ErrorContext;
    }
  ): Promise<ServiceResponse<T>> {
    try {
      const data = await this.get<T>(endpoint, params, options);
      return {
        success: true,
        data,
        metadata: {
          timestamp: new Date().toISOString()
        }
      };
    } catch (error) {
      throw error; // Let the error propagate up
    }
  }

  /**
   * Wrapped POST request that returns ServiceResponse<T>
   */
  protected async postWithWrapper<T>(
    endpoint: string, 
    data?: Record<string, unknown>,
    options?: { context?: ErrorContext }
  ): Promise<ServiceResponse<T>> {
    try {
      const result = await this.post<T>(endpoint, data, options);
      return {
        success: true,
        data: result,
        metadata: {
          timestamp: new Date().toISOString()
        }
      };
    } catch (error) {
      throw error; // Let the error propagate up
    }
  }

  /**
   * Wrapped PUT request that returns ServiceResponse<T>
   */
  protected async putWithWrapper<T>(
    endpoint: string, 
    data?: Record<string, unknown>,
    options?: { context?: ErrorContext }
  ): Promise<ServiceResponse<T>> {
    try {
      const result = await this.put<T>(endpoint, data, options);
      return {
        success: true,
        data: result,
        metadata: {
          timestamp: new Date().toISOString()
        }
      };
    } catch (error) {
      throw error; // Let the error propagate up
    }
  }

  /**
   * Wrapped DELETE request that returns ServiceResponse<T>
   */
  protected async deleteWithWrapper<T>(
    endpoint: string,
    options?: { context?: ErrorContext }
  ): Promise<ServiceResponse<T>> {
    try {
      const result = await this.delete<T>(endpoint, options);
      return {
        success: true,
        data: result,
        metadata: {
          timestamp: new Date().toISOString()
        }
      };
    } catch (error) {
      throw error; // Let the error propagate up
    }
  }
}

/**
 * Base filters interface for common query parameters
 */
export interface BaseFilters {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

/**
 * Re-export PaginatedResponse for convenience
 */
export type { PaginatedResponse } from '../../types/api';