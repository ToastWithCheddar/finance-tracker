/**
 * Centralized service exports
 * This file provides both legacy and standardized service access
 */

// Legacy services (for backward compatibility during migration)
export { TransactionService } from './transactionService';
export { default as budgetService } from './budgetService';
export { GoalService } from './goalService';
export { default as categoryService } from './categoryService';
export { default as userPreferencesService } from './userPreferencesService';
export { default as dashboardService } from './dashboardService';
export { default as mlService } from './mlService';

// Standardized services (new recommended approach)
export {
  serviceRegistry,
  transactionService as standardizedTransactionService,
  budgetService as standardizedBudgetService,
  ServiceRegistry,
  ServiceOperations,
  ServiceErrorHandler,
  createServiceHook,
} from './ServiceRegistry';

// Base service classes and utilities
export {
  BaseService,
  ServiceResult,
  ServiceCallError,
} from './base/BaseService';

// Standardized service classes
export { StandardizedTransactionService } from './standardized/TransactionService';
export { StandardizedBudgetService } from './standardized/BudgetService';

// Types
export type {
  ServiceResponse,
  ServiceError,
  PaginatedResponse,
  BaseFilters,
} from './base/BaseService';

export type { IServiceRegistry } from './ServiceRegistry';

// Core API client
export { apiClient, ApiClient } from './api';

// Utilities
export { secureStorage } from './secureStorage';
export { csrfService } from './csrf';
export { queryClient } from './queryClient';

/**
 * Migration Guide:
 * 
 * OLD WAY (Legacy):
 * ```typescript
 * import { TransactionService } from '@/services';
 * const service = new TransactionService();
 * const transactions = await service.getTransactions();
 * ```
 * 
 * NEW WAY (Standardized):
 * ```typescript
 * import { transactionService, ServiceResult } from '@/services';
 * const response = await transactionService.getTransactions();
 * const transactions = ServiceResult.unwrap(response);
 * ```
 * 
 * OR with error handling:
 * ```typescript
 * import { transactionService, ServiceResult } from '@/services';
 * const response = await transactionService.getTransactions();
 * if (ServiceResult.isSuccess(response)) {
 *   const transactions = response.data;
 * } else {
 *   console.error('Failed to load transactions:', response.error);
 * }
 * ```
 * 
 * Using service registry:
 * ```typescript
 * import { serviceRegistry } from '@/services';
 * const response = await serviceRegistry.transaction.getTransactions();
 * ```
 * 
 * Creating service hooks for React:
 * ```typescript
 * import { createServiceHook } from '@/services';
 * const useTransactionService = createServiceHook('transaction');
 * 
 * // In component:
 * const transactionService = useTransactionService();
 * ```
 */