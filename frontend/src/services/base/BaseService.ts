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
  
  // Cache for frequently accessed data
  private cache = new Map<string, { data: unknown; timestamp: number; ttl: number }>();
  
  // Default cache TTL in milliseconds (5 minutes)
  protected defaultCacheTtl = 5 * 60 * 1000;

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
   * Get data from cache if valid, otherwise return undefined
   */
  protected getCachedData<T>(key: string): T | undefined {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < cached.ttl) {
      return cached.data;
    }
    this.cache.delete(key);
    return undefined;
  }

  /**
   * Store data in cache
   */
  protected setCachedData<T>(key: string, data: T, ttl: number = this.defaultCacheTtl): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }

  /**
   * Clear cache for specific key or all cache
   */
  protected clearCache(key?: string): void {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Standard GET request with caching support
   */
  protected async get<T>(
    endpoint: string, 
    params?: Record<string, any>,
    options?: { 
      useCache?: boolean; 
      cacheTtl?: number;
      context?: ErrorContext;
    }
  ): Promise<T> {
    const cacheKey = `GET:${endpoint}:${JSON.stringify(params || {})}`;
    
    // Check cache first
    if (options?.useCache) {
      const cached = this.getCachedData<T>(cacheKey);
      if (cached) {
        return this.validateResponse(cached, endpoint);
      }
    }

    try {
      const result = await apiClient.get<T>(endpoint, params);
      
      // Validate response before caching or returning
      const validatedResult = this.validateResponse(result, endpoint);
      
      // Cache the result if caching is enabled
      if (options?.useCache) {
        this.setCachedData(cacheKey, validatedResult, options.cacheTtl);
      }
      
      return validatedResult;
    } catch (error) {
      const enhancedError = this.handleServiceError(error as ApiError, {
        ...options?.context,
        operation: 'GET',
        endpoint,
        params: params ? Object.keys(params) : undefined
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
      const result = await apiClient.post<T>(endpoint, data);
      
      // Clear related cache entries on successful POST
      this.invalidateRelatedCache(endpoint);
      
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
      const result = await apiClient.put<T>(endpoint, data);
      
      // Clear related cache entries on successful PUT
      this.invalidateRelatedCache(endpoint);
      
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
      const result = await apiClient.delete<T>(endpoint);
      
      // Clear related cache entries on successful DELETE
      this.invalidateRelatedCache(endpoint);
      
      return result;
    } catch (error) {
      throw this.handleServiceError(error as ApiError, options?.context);
    }
  }

  /**
   * Paginated GET request
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
          console.warn('Auth error - may need to refresh session');
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
   * Invalidate cache entries related to an endpoint
   */
  private invalidateRelatedCache(endpoint: string): void {
    // Clear cache entries that start with the base endpoint
    const baseEndpoint = endpoint.split('/')[1]; // Get base path
    for (const key of this.cache.keys()) {
      if (key.includes(baseEndpoint)) {
        this.cache.delete(key);
      }
    }
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
      console.error('Service Error:', logData);
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
}