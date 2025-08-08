// Comprehensive error type system for API and application errors

export interface BaseError {
  code: string;
  message: string;
  timestamp: string;
  requestId?: string;
  details?: Record<string, unknown>;
}

export interface ValidationError extends BaseError {
  field?: string;
  value?: unknown;
  constraint?: string;
}

export interface NetworkError extends BaseError {
  statusCode: number;
  retryable: boolean;
  retryAfter?: number;
}

export interface AuthError extends BaseError {
  authType: 'authentication' | 'authorization' | 'token_expired' | 'refresh_failed';
  redirectTo?: string;
}

export interface BusinessError extends BaseError {
  businessRule: string;
  context?: Record<string, unknown>;
}

export interface SystemError extends BaseError {
  systemComponent: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

// Union type for all possible errors
export type ApiError = ValidationError | NetworkError | AuthError | BusinessError | SystemError;

// Error categories for handling
export enum ErrorCategory {
  VALIDATION = 'validation',
  NETWORK = 'network', 
  AUTH = 'auth',
  BUSINESS = 'business',
  SYSTEM = 'system'
}

// Standard error codes
export const ErrorCodes = {
  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  CONNECTION_FAILED: 'CONNECTION_FAILED',
  
  // Authentication errors
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  
  // Validation errors
  VALIDATION_FAILED: 'VALIDATION_FAILED',
  REQUIRED_FIELD_MISSING: 'REQUIRED_FIELD_MISSING',
  INVALID_FORMAT: 'INVALID_FORMAT',
  VALUE_OUT_OF_RANGE: 'VALUE_OUT_OF_RANGE',
  
  // Business logic errors
  INSUFFICIENT_FUNDS: 'INSUFFICIENT_FUNDS',
  DUPLICATE_TRANSACTION: 'DUPLICATE_TRANSACTION',
  BUDGET_EXCEEDED: 'BUDGET_EXCEEDED',
  GOAL_NOT_FOUND: 'GOAL_NOT_FOUND',
  
  // System errors
  INTERNAL_SERVER_ERROR: 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
  DATABASE_ERROR: 'DATABASE_ERROR'
} as const;

export type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];

// Error response from API
export interface ApiErrorResponse {
  error: {
    code: ErrorCode;
    message: string;
    details?: Record<string, unknown>;
    field?: string;
    timestamp: string;
    requestId?: string;
  };
}

// Error recovery strategies
export interface ErrorRecoveryStrategy {
  canRetry: boolean;
  retryDelay?: number;
  maxRetries?: number;
  fallbackAction?: () => void;
  userMessage?: string;
}

// Error context for logging and debugging
export interface ErrorContext {
  userId?: string;
  sessionId?: string;
  feature: string;
  action: string;
  metadata?: Record<string, unknown>;
}