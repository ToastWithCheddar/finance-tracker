"""
Custom exception classes for the finance tracker application.

These exceptions provide specific error types that can be caught and handled
appropriately by the API layer while avoiding information leakage.
"""

from typing import Optional, Any, Dict


class FinanceTrackerException(Exception):
    """Base exception for all finance tracker specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(FinanceTrackerException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str = "Invalid input data", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AuthenticationError(FinanceTrackerException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(FinanceTrackerException):
    """Raised when user is not authorized to access a resource."""
    
    def __init__(self, message: str = "Not authorized to access this resource"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403
        )


class ResourceNotFoundError(FinanceTrackerException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Optional[str] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with ID: {resource_id}"
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404
        )


class AccountNotFoundError(ResourceNotFoundError):
    """Raised when an account is not found."""
    
    def __init__(self, account_id: Optional[str] = None):
        super().__init__("Account", account_id)


class TransactionNotFoundError(ResourceNotFoundError):
    """Raised when a transaction is not found."""
    
    def __init__(self, transaction_id: Optional[str] = None):
        super().__init__("Transaction", transaction_id)


class BudgetNotFoundError(ResourceNotFoundError):
    """Raised when a budget is not found."""
    
    def __init__(self, budget_id: Optional[str] = None):
        super().__init__("Budget", budget_id)


class GoalNotFoundError(ResourceNotFoundError):
    """Raised when a goal is not found."""
    
    def __init__(self, goal_id: Optional[str] = None):
        super().__init__("Goal", goal_id)


class CategoryNotFoundError(ResourceNotFoundError):
    """Raised when a category is not found."""
    
    def __init__(self, category_id: Optional[str] = None):
        super().__init__("Category", category_id)


class CategorizationRuleNotFoundError(ResourceNotFoundError):
    """Raised when a categorization rule is not found."""
    
    def __init__(self, rule_id: Optional[str] = None):
        super().__init__("Categorization rule", rule_id)


class DuplicateResourceError(FinanceTrackerException):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(self, resource_type: str, message: Optional[str] = None):
        if not message:
            message = f"{resource_type} already exists"
        
        super().__init__(
            message=message,
            error_code="DUPLICATE_RESOURCE",
            status_code=409
        )


class PlaidIntegrationError(FinanceTrackerException):
    """Raised when Plaid API integration fails."""
    
    def __init__(self, message: str = "Plaid service unavailable", plaid_error_code: Optional[str] = None):
        details = {}
        if plaid_error_code:
            details["plaid_error_code"] = plaid_error_code
        
        super().__init__(
            message=message,
            error_code="PLAID_INTEGRATION_ERROR",
            status_code=502,
            details=details
        )


class ExternalServiceError(FinanceTrackerException):
    """Raised when an external service is unavailable or returns an error."""
    
    def __init__(self, service_name: str, message: str = "External service unavailable"):
        super().__init__(
            message=f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502
        )


class BusinessLogicError(FinanceTrackerException):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str, error_code: str = "BUSINESS_LOGIC_ERROR"):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400
        )


class InsufficientFundsError(BusinessLogicError):
    """Raised when a transaction would result in insufficient funds."""
    
    def __init__(self, message: str = "Insufficient funds for this transaction"):
        super().__init__(message, "INSUFFICIENT_FUNDS")


class BudgetExceededError(BusinessLogicError):
    """Raised when a transaction would exceed a budget limit."""
    
    def __init__(self, message: str = "Transaction would exceed budget limit"):
        super().__init__(message, "BUDGET_EXCEEDED")


class DataIntegrityError(FinanceTrackerException):
    """Raised when data integrity constraints are violated."""
    
    def __init__(self, message: str = "Data integrity violation"):
        super().__init__(
            message=message,
            error_code="DATA_INTEGRITY_ERROR",
            status_code=422
        )


class RateLimitError(FinanceTrackerException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429
        )


class ConfigurationError(FinanceTrackerException):
    """Raised when there's a configuration issue."""
    
    def __init__(self, message: str = "Configuration error"):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500
        )


class MLServiceError(FinanceTrackerException):
    """Raised when ML service operations fail."""
    
    def __init__(self, message: str = "Machine learning service unavailable"):
        super().__init__(
            message=message,
            error_code="ML_SERVICE_ERROR",
            status_code=503
        )