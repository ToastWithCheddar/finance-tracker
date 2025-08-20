"""
Error response schemas for standardized API error handling.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorDetail(BaseModel):
    """Individual error detail"""
    
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code for programmatic handling")


class ErrorResponse(BaseModel):
    """Standardized error response schema"""
    
    error: bool = Field(True, description="Always true for error responses")
    message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(..., description="When the error occurred")
    path: str = Field(..., description="API path that caused the error")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "Resource not found",
                "error_code": "RESOURCE_NOT_FOUND",
                "status_code": 404,
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/accounts/123",
                "request_id": "req_1234567890",
                "details": {}
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """Error response for validation failures"""
    
    validation_errors: list[ErrorDetail] = Field(
        ..., 
        description="List of validation errors"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "Validation failed",
                "error_code": "VALIDATION_ERROR",
                "status_code": 422,
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/transactions",
                "request_id": "req_1234567890",
                "details": {},
                "validation_errors": [
                    {
                        "field": "amount",
                        "message": "Amount must be greater than 0",
                        "code": "VALUE_ERROR"
                    }
                ]
            }
        }


class AuthenticationErrorResponse(ErrorResponse):
    """Error response for authentication failures"""
    
    auth_scheme: Optional[str] = Field(None, description="Authentication scheme required")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "Authentication required",
                "error_code": "AUTHENTICATION_ERROR",
                "status_code": 401,
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/accounts",
                "request_id": "req_1234567890",
                "details": {},
                "auth_scheme": "Bearer"
            }
        }


class AuthorizationErrorResponse(ErrorResponse):
    """Error response for authorization failures"""
    
    required_permission: Optional[str] = Field(None, description="Required permission")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "Access denied",
                "error_code": "AUTHORIZATION_ERROR", 
                "status_code": 403,
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/accounts/123",
                "request_id": "req_1234567890",
                "details": {},
                "required_permission": "account:read"
            }
        }


class RateLimitErrorResponse(ErrorResponse):
    """Error response for rate limit exceeded"""
    
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
    limit: Optional[str] = Field(None, description="Rate limit that was exceeded")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "status_code": 429,
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/transactions",
                "request_id": "req_1234567890",
                "details": {},
                "retry_after": 60,
                "limit": "1000 per minute"
            }
        }


class ExternalServiceErrorResponse(ErrorResponse):
    """Error response for external service failures"""
    
    service_name: str = Field(..., description="Name of the failed external service")
    service_status: Optional[str] = Field(None, description="Status of the external service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "External service unavailable",
                "error_code": "EXTERNAL_SERVICE_ERROR",
                "status_code": 502,
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/accounts/plaid/link",
                "request_id": "req_1234567890",
                "details": {},
                "service_name": "Plaid",
                "service_status": "degraded"
            }
        }