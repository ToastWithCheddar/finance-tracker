/**
 * Centralized service exports
 * This file provides both legacy and standardized service access
 */

// Enhanced consolidated services (single implementation)
export { TransactionService, transactionService } from './transactionService';
export { BudgetService, budgetService } from './budgetService';
export { BudgetAlertService, budgetAlertService } from './budgetAlertService';
export { GoalService } from './goalService';
export { categoryService } from './categoryService';
export { dashboardService } from './dashboardService';
export { mlService } from './mlService';
export { NotificationService } from './notificationService';

// Service registry (now uses consolidated services)
export {
  serviceRegistry,
  registryTransactionService,
  registryBudgetService,
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