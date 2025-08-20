/**
 * Centralized service exports
 * This file provides both legacy and standardized service access
 */

// Enhanced consolidated services (single implementation)
export { TransactionService, transactionService } from './transactionService';
export { BudgetService, budgetService } from './budgetService';
export { GoalService } from './goalService';
export { categoryService } from './categoryService';
export { dashboardService } from './dashboardService';
export { mlService } from './mlService';
export { NotificationService } from './notificationService';
export { timelineService } from './timelineService';
export { savedFilterService } from './savedFilterService';
export { plaidRecurringService } from './plaidRecurringService';
export { categorizationRulesService } from './categorizationRulesService';

// Service registry (now uses consolidated services)
export {
  serviceRegistry,
  registryTransactionService,
  registryBudgetService,
  registrySavedFilterService,
  registryTimelineService,
  ServiceRegistry,
  ServiceOperations,
  ServiceErrorHandler,
  createServiceHook,
} from './ServiceRegistry';

// Base service classes and utilities
export {
  BaseService,
  type ServiceResult,
} from './base/BaseService';

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
 * Usage Guide (Consolidated Services):
 * 
 * DIRECT SERVICE ACCESS:
 * ```typescript
 * import { transactionService, budgetService } from '@/services';
 * 
 * // Returns raw data (backward compatible)
 * const transactions = await transactionService.getTransactions();
 * 
 * // Returns ServiceResponse wrapper (new pattern)
 * const response = await transactionService.getTransactionsWithWrapper();
 * if (response.success) {
 *   const transactions = response.data;
 * }
 * ```
 * 
 * SERVICE REGISTRY ACCESS:
 * ```typescript
 * import { serviceRegistry } from '@/services';
 * const transactions = await serviceRegistry.transaction.getTransactions();
 * const budgets = await serviceRegistry.budget.getBudgets();
 * ```
 * 
 * CREATING SERVICE HOOKS FOR REACT:
 * ```typescript
 * import { createServiceHook } from '@/services';
 * const useTransactionService = createServiceHook('transaction');
 * 
 * // In component:
 * const transactionService = useTransactionService();
 * ```
 * 
 * ENHANCED FEATURES:
 * ```typescript
 * import { transactionService, budgetService } from '@/services';
 * 
 * // New transaction features
 * const trends = await transactionService.getSpendingTrends('month');
 * const breakdown = await transactionService.getCategoryBreakdown();
 * 
 * // New budget features  
 * const analytics = await budgetService.getBudgetAnalytics();
 * const comparison = await budgetService.getBudgetComparison(start1, end1, start2, end2);
 * ```
 */