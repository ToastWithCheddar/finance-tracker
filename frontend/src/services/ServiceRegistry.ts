/**
 * Service Registry for centralized service management
 * Provides standardized access to all application services
 */
import { StandardizedTransactionService } from './standardized/TransactionService';
import { StandardizedBudgetService } from './standardized/BudgetService';
import { type ServiceResponse, type ServiceError, type ServiceResult } from './base/BaseService';

// Service instances
const services = {
  transaction: new StandardizedTransactionService(),
  budget: new StandardizedBudgetService(),
  // Add other services as they're standardized
} as const;

// Service registry interface
export interface IServiceRegistry {
  readonly transaction: StandardizedTransactionService;
  readonly budget: StandardizedBudgetService;
}

/**
 * Central service registry providing standardized access to all services
 */
export class ServiceRegistry implements IServiceRegistry {
  private static instance: ServiceRegistry;
  
  readonly transaction = services.transaction;
  readonly budget = services.budget;
  
  private constructor() {
    // Private constructor for singleton
  }
  
  /**
   * Get the singleton instance of the service registry
   */
  static getInstance(): ServiceRegistry {
    if (!ServiceRegistry.instance) {
      ServiceRegistry.instance = new ServiceRegistry();
    }
    return ServiceRegistry.instance;
  }
  
  /**
   * Health check for all services
   */
  async healthCheck(): Promise<{ [K in keyof IServiceRegistry]: boolean }> {
    // Simple health check - could be expanded to actual service health endpoints
    try {
      return {
        transaction: true,
        budget: true,
      };
    } catch (error) {
      console.error('Service health check failed:', error);
      return {
        transaction: false,
        budget: false,
      };
    }
  }
  
  /**
   * Get service statistics
   */
  getServiceStats() {
    return {
      registeredServices: Object.keys(services).length,
      availableServices: Object.keys(services),
      lastHealthCheck: new Date().toISOString(),
    };
  }
}

// Export singleton instance
export const serviceRegistry = ServiceRegistry.getInstance();

// Export individual services for direct access
export const {
  transaction: transactionService,
  budget: budgetService,
} = serviceRegistry;

// Re-export service utilities
export type { ServiceResponse, ServiceError, ServiceResult };
export type { ServiceResponse as StandardServiceResponse };

// Service hook factory for React components
export function createServiceHook<T extends keyof IServiceRegistry>(serviceName: T) {
  return () => serviceRegistry[serviceName];
}

// Common service operations wrapper
export class ServiceOperations {
  /**
   * Execute multiple service calls and combine results
   */
  static async parallel<T extends Record<string, Promise<ServiceResponse<unknown>>>>(
    operations: T
  ): Promise<{ [K in keyof T]: Awaited<T[K]> }> {
    const entries = Object.entries(operations);
    const results = await Promise.all(entries.map(([key, promise]) => 
      promise.then(result => [key, result] as const)
    ));
    
    return Object.fromEntries(results) as { [K in keyof T]: Awaited<T[K]> };
  }
  
  /**
   * Execute service calls in sequence with early termination on error
   */
  static async sequence<T>(
    operations: Array<() => Promise<ServiceResult<T>>>
  ): Promise<ServiceResult<T[]>> {
    const results: T[] = [];
    
    for (const operation of operations) {
      const result = await operation();
      
      if (!result.success) {
        return {
          success: false,
          error: result.error,
          metadata: {
            timestamp: new Date().toISOString(),
            completedOperations: results.length,
            totalOperations: operations.length
          }
        };
      }
      
      if (result.success && result.data !== undefined) {
        results.push(result.data);
      }
    }
    
    return {
      success: true,
      data: results,
      metadata: {
        timestamp: new Date().toISOString(),
        completedOperations: results.length,
        totalOperations: operations.length
      }
    };
  }
  
  /**
   * Retry a service operation with exponential backoff
   */
  static async retry<T>(
    operation: () => Promise<ServiceResult<T>>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<ServiceResult<T>> {
    let lastError: ServiceError | undefined;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const result = await operation();
        
        if (result.success) {
          return result;
        }
        
        lastError = result.error;
        
        // Don't retry on client errors (4xx)
        if (result.error?.status && result.error.status >= 400 && result.error.status < 500) {
          return result;
        }
        
        // Wait before retrying (exponential backoff)
        if (attempt < maxRetries) {
          const delay = baseDelay * Math.pow(2, attempt);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      } catch (error) {
        lastError = {
          code: 'RETRY_FAILED',
          message: error instanceof Error ? error.message : 'Retry operation failed'
        };
      }
    }
    
    return {
      success: false,
      error: lastError || {
        code: 'MAX_RETRIES_EXCEEDED',
        message: `Operation failed after ${maxRetries} retries`
      },
      metadata: {
        timestamp: new Date().toISOString(),
        retries: maxRetries
      }
    };
  }
}

// Error boundary helper for service calls in React components
export class ServiceErrorHandler {
  /**
   * Handle service errors with user-friendly messages
   */
  static handleError(error: ServiceError): string {
    switch (error.code) {
      case 'NETWORK_ERROR':
        return 'Network connection issue. Please check your internet connection.';
      case 'TIMEOUT':
        return 'Request timed out. Please try again.';
      case 'HTTP_401':
        return 'Authentication required. Please log in again.';
      case 'HTTP_403':
        return 'Access denied. You do not have permission for this action.';
      case 'HTTP_404':
        return 'The requested resource was not found.';
      case 'HTTP_429':
        return 'Too many requests. Please wait a moment and try again.';
      case 'HTTP_500':
      case 'HTTP_502':
      case 'HTTP_503':
        return 'Server error. Please try again later.';
      default:
        return error.message || 'An unexpected error occurred.';
    }
  }
  
  /**
   * Check if error is retryable
   */
  static isRetryable(error: ServiceError): boolean {
    const retryableCodes = ['NETWORK_ERROR', 'TIMEOUT', 'HTTP_502', 'HTTP_503', 'HTTP_504'];
    return retryableCodes.includes(error.code);
  }
  
  /**
   * Get error severity level
   */
  static getErrorSeverity(error: ServiceError): 'low' | 'medium' | 'high' | 'critical' {
    if (error.status && error.status >= 500) return 'critical';
    if (error.code === 'NETWORK_ERROR' || error.code === 'TIMEOUT') return 'high';
    if (error.status && error.status >= 400) return 'medium';
    return 'low';
  }
}