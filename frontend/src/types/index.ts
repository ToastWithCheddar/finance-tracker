// Re-export all types for easier imports
export type * from './auth';
export type * from './transaction';
export type * from './category';
export type * from './goals';
export type * from './budgets';
export type * from './websocket';
export type * from './ml';

// Re-export specific types from api to avoid conflicts with errors
export type {
  ApiResponse,
  PaginationParams,
  PaginatedResponse,
  HttpMethod,
  RequestOptions
} from './api';

// Re-export specific types from errors to avoid conflicts with api
export type {
  BaseError,
  ValidationError,
  NetworkError,
  AuthError,
  BusinessError,
  SystemError,
  ErrorCategory,
  ErrorCode,
  ApiErrorResponse,
  ErrorRecoveryStrategy,
  ErrorContext
} from './errors';

// Use aliases for conflicting types
export type { ApiError as ApiErrorType } from './api';
export type { ApiError as ComprehensiveApiError } from './errors';

// Re-export specific types from realtime to avoid conflicts
export type {
  AccountSummary,
  CategorySpending,
  DashboardData,
  RealtimeTransaction,
  RealtimeNotification,
  AccountBalance,
  GoalProgress
} from './realtime';

// Use specific aliases for conflicting types
export type { BudgetAlert as RealtimeBudgetAlert } from './realtime';
export type { ConnectionStatus as RealtimeConnectionStatus } from './realtime';

// Re-export const values (not types)
export { ErrorCodes } from './errors';