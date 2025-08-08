"""
Global exception handler middleware for standardized error responses
"""
import uuid
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError
import traceback

from ..core.exceptions import (
    BaseAppException,
    StandardErrorResponse,
    ErrorCode,
    ErrorSeverity,
    ErrorDetail,
    DatabaseException,
    ValidationException,
    handle_database_error
)

logger = logging.getLogger(__name__)

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handler middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = None
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
            
        except BaseAppException as exc:
            # Handle application-specific exceptions
            return await self._handle_app_exception(exc, request, request_id)
            
        except RequestValidationError as exc:
            # Handle Pydantic validation errors
            return await self._handle_validation_error(exc, request, request_id)
            
        except HTTPException as exc:
            # Handle FastAPI HTTP exceptions
            return await self._handle_http_exception(exc, request, request_id)
            
        except StarletteHTTPException as exc:
            # Handle Starlette HTTP exceptions
            return await self._handle_starlette_exception(exc, request, request_id)
            
        except SQLAlchemyError as exc:
            # Handle database errors
            return await self._handle_database_error(exc, request, request_id)
            
        except Exception as exc:
            # Handle unexpected errors
            return await self._handle_unexpected_error(exc, request, request_id)
    
    async def _handle_app_exception(
        self, 
        exc: BaseAppException, 
        request: Request, 
        request_id: str
    ) -> JSONResponse:
        """Handle application-specific exceptions"""
        # Get user ID if available
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            exc.user_id = str(user_id)
        
        # Create standardized response
        error_response = exc.to_response(
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        # Log the error
        exc.log_error(request_id)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(),
            headers={"X-Request-ID": request_id}
        )
    
    async def _handle_validation_error(
        self, 
        exc: RequestValidationError, 
        request: Request, 
        request_id: str
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        details = []
        
        for error in exc.errors():
            field_name = ".".join(str(loc) for loc in error["loc"])
            details.append(ErrorDetail(
                field=field_name,
                message=error["msg"],
                code=error["type"],
                value=error.get("input")
            ))
        
        error_response = StandardErrorResponse(
            error=ErrorCode.VALIDATION_ERROR,
            message="Validation failed",
            details=details,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            severity=ErrorSeverity.LOW
        )
        
        # Log validation error
        logger.warning(
            f"Validation error: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "errors": [error.model_dump() for error in details],
                "user_id": getattr(request.state, 'user_id', None)
            }
        )
        
        return JSONResponse(
            status_code=422,
            content=error_response.model_dump(),
            headers={"X-Request-ID": request_id}
        )
    
    async def _handle_http_exception(
        self, 
        exc: HTTPException, 
        request: Request, 
        request_id: str
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        # Check if detail is already a standardized error response
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            # Already standardized, just add request ID
            exc.detail["request_id"] = request_id
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers={"X-Request-ID": request_id}
            )
        
        # Convert to standardized format
        error_code = self._status_to_error_code(exc.status_code)
        message = str(exc.detail) if exc.detail else "HTTP error"
        
        error_response = StandardErrorResponse(
            error=error_code,
            message=message,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            severity=self._status_to_severity(exc.status_code)
        )
        
        # Log HTTP error
        logger.warning(
            f"HTTP error {exc.status_code}: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "user_id": getattr(request.state, 'user_id', None)
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(),
            headers={"X-Request-ID": request_id}
        )
    
    async def _handle_starlette_exception(
        self, 
        exc: StarletteHTTPException, 
        request: Request, 
        request_id: str
    ) -> JSONResponse:
        """Handle Starlette HTTP exceptions"""
        error_code = self._status_to_error_code(exc.status_code)
        message = str(exc.detail) if exc.detail else "HTTP error"
        
        error_response = StandardErrorResponse(
            error=error_code,
            message=message,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            severity=self._status_to_severity(exc.status_code)
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(),
            headers={"X-Request-ID": request_id}
        )
    
    async def _handle_database_error(
        self, 
        exc: SQLAlchemyError, 
        request: Request, 
        request_id: str
    ) -> JSONResponse:
        """Handle database errors"""
        operation = f"{request.method} {request.url.path}"
        db_exception = handle_database_error(exc, operation)
        
        # Add request context
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            db_exception.user_id = str(user_id)
        
        return await self._handle_app_exception(db_exception, request, request_id)
    
    async def _handle_unexpected_error(
        self, 
        exc: Exception, 
        request: Request, 
        request_id: str
    ) -> JSONResponse:
        """Handle unexpected errors"""
        # Log the full traceback
        logger.critical(
            f"Unexpected error: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "user_id": getattr(request.state, 'user_id', None),
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        
        error_response = StandardErrorResponse(
            error=ErrorCode.INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            severity=ErrorSeverity.CRITICAL
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(),
            headers={"X-Request-ID": request_id}
        )
    
    def _status_to_error_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to error codes"""
        status_map = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.RESOURCE_NOT_FOUND,
            409: ErrorCode.RESOURCE_CONFLICT,
            422: ErrorCode.VALIDATION_ERROR,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
            500: ErrorCode.INTERNAL_SERVER_ERROR,
            503: ErrorCode.ML_SERVICE_UNAVAILABLE,
        }
        return status_map.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR)
    
    def _status_to_severity(self, status_code: int) -> ErrorSeverity:
        """Map HTTP status codes to severity levels"""
        if status_code >= 500:
            return ErrorSeverity.CRITICAL
        elif status_code >= 400:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

# Request context middleware to add user info to errors
class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context for error handling"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Try to extract user ID from auth header or JWT
        try:
            # This would be implemented based on your auth system
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Extract user ID from JWT token (simplified)
                # In real implementation, you'd decode the JWT
                request.state.user_id = "extracted_from_jwt"
        except Exception:
            # Don't fail request if user extraction fails
            pass
        
        return await call_next(request)