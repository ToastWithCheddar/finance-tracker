"""
Standardized exception handling for the Finance Tracker application
"""
from typing import Any, Dict, Optional, List, Union
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
import logging
import traceback
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorCode(str, Enum):
    """Standardized error codes"""
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Resource Errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    
    # Business Logic Errors
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    GOAL_ALREADY_ACHIEVED = "GOAL_ALREADY_ACHIEVED"
    CATEGORY_IN_USE = "CATEGORY_IN_USE"
    ACCOUNT_SYNC_FAILED = "ACCOUNT_SYNC_FAILED"
    
    # External Service Errors
    ML_SERVICE_UNAVAILABLE = "ML_SERVICE_UNAVAILABLE"
    PLAID_SERVICE_ERROR = "PLAID_SERVICE_ERROR"
    EMAIL_SERVICE_ERROR = "EMAIL_SERVICE_ERROR"
    
    # System Errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field name if applicable")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Specific error code")
    value: Optional[Any] = Field(None, description="Invalid value if applicable")

class StandardErrorResponse(BaseModel):
    """Standardized error response structure"""
    error: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: List[ErrorDetail] = Field(default_factory=list, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    path: Optional[str] = Field(None, description="API path where error occurred")
    method: Optional[str] = Field(None, description="HTTP method")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    severity: ErrorSeverity = Field(ErrorSeverity.MEDIUM, description="Error severity level")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BaseAppException(Exception):
    """Base exception class for application-specific errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        details: Optional[List[ErrorDetail]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or []
        self.severity = severity
        self.status_code = status_code
        self.user_id = user_id
        self.context = context or {}
        super().__init__(self.message)
    
    def to_response(self, request_id: Optional[str] = None, path: Optional[str] = None, method: Optional[str] = None) -> StandardErrorResponse:
        """Convert exception to standardized error response"""
        return StandardErrorResponse(
            error=self.error_code,
            message=self.message,
            details=self.details,
            request_id=request_id,
            path=path,
            method=method,
            user_id=self.user_id,
            severity=self.severity
        )
    
    def log_error(self, request_id: Optional[str] = None):
        """Log the error with appropriate level based on severity"""
        log_data = {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity,
            "status_code": self.status_code,
            "user_id": self.user_id,
            "request_id": request_id,
            "context": self.context
        }
        
        if self.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error(f"Application error: {self.error_code}", extra=log_data, exc_info=True)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Application warning: {self.error_code}", extra=log_data)
        else:
            logger.info(f"Application info: {self.error_code}", extra=log_data)

# Specific exception classes
class ValidationException(BaseAppException):
    """Validation error exception"""
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None, field: Optional[str] = None):
        if field and not details:
            details = [ErrorDetail(field=field, message=message)]
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            severity=ErrorSeverity.LOW,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class ResourceNotFoundException(BaseAppException):
    """Resource not found exception"""
    def __init__(self, resource_type: str, resource_id: Optional[str] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            severity=ErrorSeverity.LOW,
            status_code=status.HTTP_404_NOT_FOUND
        )

class ResourceConflictException(BaseAppException):
    """Resource conflict exception"""
    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            severity=ErrorSeverity.MEDIUM,
            status_code=status.HTTP_409_CONFLICT,
            context={"resource_type": resource_type} if resource_type else None
        )

class AuthenticationException(BaseAppException):
    """Authentication error exception"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            severity=ErrorSeverity.MEDIUM,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationException(BaseAppException):
    """Authorization error exception"""
    def __init__(self, message: str = "Access denied", user_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            severity=ErrorSeverity.HIGH,
            status_code=status.HTTP_403_FORBIDDEN,
            user_id=user_id
        )

class BusinessLogicException(BaseAppException):
    """Business logic error exception"""
    def __init__(self, message: str, error_code: ErrorCode, details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class ExternalServiceException(BaseAppException):
    """External service error exception"""
    def __init__(self, service_name: str, message: str, error_code: ErrorCode):
        super().__init__(
            message=f"{service_name}: {message}",
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            context={"service_name": service_name}
        )

class DatabaseException(BaseAppException):
    """Database error exception"""
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            severity=ErrorSeverity.CRITICAL,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context={"operation": operation} if operation else None
        )

class ConfigurationException(BaseAppException):
    """Configuration error exception"""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.CRITICAL,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context={"config_key": config_key} if config_key else None
        )

class RateLimitException(BaseAppException):
    """Rate limit exceeded exception"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            severity=ErrorSeverity.MEDIUM,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            context={"retry_after": retry_after} if retry_after else None
        )

# Utility functions for error handling
def create_validation_error(field: str, message: str, value: Any = None) -> ErrorDetail:
    """Create a validation error detail"""
    return ErrorDetail(
        field=field,
        message=message,
        code=ErrorCode.VALIDATION_ERROR,
        value=value
    )

def create_http_exception(
    app_exception: BaseAppException, 
    request_id: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None
) -> HTTPException:
    """Convert application exception to FastAPI HTTPException"""
    response = app_exception.to_response(request_id, path, method)
    app_exception.log_error(request_id)
    
    return HTTPException(
        status_code=app_exception.status_code,
        detail=response.model_dump()
    )

def handle_database_error(error: Exception, operation: str) -> DatabaseException:
    """Handle database errors with proper logging"""
    error_message = str(error)
    
    # Log the original database error
    logger.error(f"Database error during {operation}: {error_message}", exc_info=True)
    
    # Create user-friendly message
    if "unique constraint" in error_message.lower():
        return DatabaseException(
            message="A record with these details already exists",
            operation=operation
        )
    elif "foreign key" in error_message.lower():
        return DatabaseException(
            message="Cannot complete operation due to related data constraints",
            operation=operation
        )
    elif "not null" in error_message.lower():
        return DatabaseException(
            message="Required information is missing",
            operation=operation
        )
    else:
        return DatabaseException(
            message="Database operation failed",
            operation=operation
        )