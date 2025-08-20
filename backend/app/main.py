from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.trustedhost import TrustedHostMiddleware  # Not needed for development
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
import logging
import time
from datetime import datetime, timezone

from app.config import settings
from app.database import engine, check_database_health, create_database
from app.models import Base
from app.routes import auth, users, health, categories, transactions, budget, analytics, webhooks, notifications, ml, saved_filters, websockets, categorization_rules, merchants
from app.routes import accounts_basic, accounts_plaid, accounts_sync, accounts_reconciliation
from app.routes import recurring_plaid
from app.core.exceptions import FinanceTrackerException
from app.schemas.error import ErrorResponse, ValidationErrorResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


# Configure logging for development
level_name = str(getattr(settings, "LOG_LEVEL", "DEBUG")).upper()
# Robust conversion: supports INFO/DEBUG/WARNING… and falls back to DEBUG for dev
log_level = logging.getLevelNamesMapping().get(level_name, logging.DEBUG)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        # No file logging in development to avoid clutter
    ]
)
logger = logging.getLogger(__name__)
# Relaxed rate limiting for development
limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Finance Tracker API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug: {settings.DEBUG}")
    logger.info(f"Database Enabled: {settings.ENABLE_DATABASE}")
    
    # Skip database setup if disabled
    if not settings.ENABLE_DATABASE:
        logger.info("⚠️ Database setup skipped (disabled)")
    else:
        # Create database if it does not exist
        create_database()
        
        # Check database connection
        if not check_database_health():
            logger.error("❌ Database connection failed")
            raise RuntimeError("Database connection failed")
    
        # Create tables
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise RuntimeError(f"Database initialization failed: {e}")
        
        # Initialize default data
        try:
            from app.scripts.seed_data import seed_default_categories
            seed_default_categories()
            logger.info("✅ Default data initialized")
        except Exception as e:
            logger.warning(f"⚠️ Default data initialization failed: {e}")
    
    # Initialize financial health service with configuration
    try:
        from app.services.financial_health_service import get_financial_health_service
        health_service = get_financial_health_service(settings.financial_health_config)
        logger.info("✅ Financial health service initialized with configuration")
    except Exception as e:
        logger.warning(f"⚠️ Financial health service initialization failed: {e}")
    
    logger.info("🎉 Finance Tracker API started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Finance Tracker API...")

# Create FastAPI app - Development Configuration
app = FastAPI(
    title="Finance Tracker API (Development)",
    description="A comprehensive personal finance management API with AI-powered insights - DEVELOPMENT MODE",
    version="1.0.0-dev",
    docs_url="/docs",  # Always enabled in development
    redoc_url="/redoc",  # Always enabled in development
    openapi_url="/openapi.json",  # Always enabled in development
    lifespan=lifespan,
    contact={
        "name": "Finance Tracker Development",
        "email": "dev@financetracker.local",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
    expose_headers=["X-Process-Time", "X-Request-ID"],
)
app.add_middleware(SlowAPIMiddleware)

# Disable Trusted Host Middleware for development flexibility
# if settings.ENVIRONMENT == "production":
#     app.add_middleware(
#         TrustedHostMiddleware,
#         allowed_hosts=["*.financetracker.com", "financetracker.com", "localhost"]
#     )

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Add request ID for tracing
    request_id = f"req_{int(time.time() * 1000000)}"
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s - "
        f"ID: {request_id}"
    )
    
    return response

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Disable HSTS in development
    # if settings.ENVIRONMENT == "production":
    #     response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Exception handlers
@app.exception_handler(FinanceTrackerException)
async def finance_tracker_exception_handler(request: Request, exc: FinanceTrackerException):
    """Handler for custom finance tracker exceptions"""
    # Log the full exception details internally
    logger.error(
        f"Finance Tracker Exception: {exc.error_code} - {exc.message} - Path: {request.url.path}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": str(request.url.path)
        },
        exc_info=True
    )
    
    # Get request ID from headers if available
    request_id = getattr(request.state, 'request_id', None)
    if not request_id and hasattr(request, 'headers'):
        request_id = request.headers.get('X-Request-ID')
    
    # Return safe error response to client
    error_response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        status_code=exc.status_code,
        timestamp=datetime.now(timezone.utc),
        path=str(request.url.path),
        request_id=request_id,
        details=exc.details if not _is_sensitive_details(exc.details) else {}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    # Log HTTP exceptions
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    
    # Return standardized response
    request_id = getattr(request.state, 'request_id', None) or request.headers.get('X-Request-ID')
    
    error_response = ErrorResponse(
        message=exc.detail if isinstance(exc.detail, str) else "HTTP error occurred",
        error_code=f"HTTP_{exc.status_code}",
        status_code=exc.status_code,
        timestamp=datetime.now(timezone.utc),
        path=str(request.url.path),
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler"""
    # Log validation errors with details
    logger.error(
        f"Validation error: {exc.errors()} - Path: {request.url.path}",
        extra={"validation_errors": exc.errors(), "path": str(request.url.path)}
    )
    
    request_id = getattr(request.state, 'request_id', None) or request.headers.get('X-Request-ID')
    
    # Transform validation errors to safe format
    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        validation_errors.append({
            "field": field if field else None,
            "message": error.get("msg", "Validation error"),
            "code": error.get("type", "validation_error")
        })
    
    error_response = ValidationErrorResponse(
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        status_code=422,
        timestamp=datetime.now(timezone.utc),
        path=str(request.url.path),
        request_id=request_id,
        validation_errors=validation_errors
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unhandled exceptions"""
    # Log full exception details internally
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)} - Path: {request.url.path}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )
    
    request_id = getattr(request.state, 'request_id', None) or request.headers.get('X-Request-ID')
    
    # Return generic error message to client (never expose internal details)
    error_response = ErrorResponse(
        message="An internal server error occurred. Please try again later.",
        error_code="INTERNAL_SERVER_ERROR",
        status_code=500,
        timestamp=datetime.now(timezone.utc),
        path=str(request.url.path),
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )

def _is_sensitive_details(details: dict) -> bool:
    """Check if error details contain sensitive information that should not be exposed."""
    if not details:
        return False
    
    sensitive_keys = {
        'password', 'token', 'secret', 'key', 'auth', 'credential', 
        'database', 'connection', 'stacktrace', 'traceback', 'exception'
    }
    
    for key in details.keys():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            return True
    
    return False

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Finance Tracker API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs" if settings.DEBUG else None,
        "health": "/health",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# Include routers
app.include_router(
    health.router,
    tags=["Health"],
    responses={
        200: {"description": "Success"},
        503: {"description": "Service Unavailable"},
    }
)

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    users.router,
    prefix="/api/users",
    tags=["Users"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
    }
)

app.include_router(
    categories.router,
    prefix="/api/categories",
    tags=["Categories"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
    }
)

app.include_router(
    transactions.router,
    prefix="/api/transactions",
    tags=["Transactions"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    recurring_plaid.router,
    prefix="/api/recurring",
    tags=["Recurring Transactions"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    budget.router,
    prefix="/api/budgets",
    tags=["Budgets"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)


app.include_router(
    accounts_basic.router,
    prefix="/api/accounts",
    tags=["Accounts - Basic Operations"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    accounts_plaid.router,
    prefix="/api/accounts",
    tags=["Accounts - Plaid Integration"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    accounts_sync.router,
    prefix="/api/accounts",
    tags=["Accounts - Synchronization"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    accounts_reconciliation.router,
    prefix="/api/accounts",
    tags=["Accounts - Reconciliation & Health"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["Analytics & Dashboard"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)


app.include_router(
    webhooks.router,
    prefix="/api",
    tags=["Webhooks"],
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    }
)

app.include_router(
    ml.router,
    prefix="/api",
    responses={
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    notifications.router,
    prefix="/api",
    tags=["Notifications"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)


app.include_router(
    saved_filters.router,
    prefix="/api",
    tags=["Saved Filters"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)


app.include_router(
    categorization_rules.router,
    prefix="/api",
    tags=["Categorization Rules"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    merchants.router,
    prefix="/api",
    tags=["Merchant Recognition"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

# Realtime WebSocket routes (no prefix)
app.include_router(
    websockets.router,
    tags=["Realtime"],
)


# API versioning (future use)
@app.get("/api", tags=["API Info"])
async def api_base():
    """Base API endpoint"""
    return {
        "message": "Finance Tracker API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "auth": "/api/auth",
            "users": "/api/users", 
            "categories": "/api/categories",
            "transactions": "/api/transactions",
            "recurring": "/api/recurring",
            "budgets": "/api/budgets",
            "accounts": "/api/accounts",
            "analytics": "/api/analytics",
            "webhooks": "/api/webhooks",
            "notifications": "/api/notifications",
            "saved_filters": "/api/saved-filters",
            "categorization_rules": "/api/categorization-rules",
            "merchants": "/api/merchants",
            "ml": "/api/ml",
            "health": "/health",
            "docs": "/docs" if settings.DEBUG else None,
        },
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/info", tags=["API Info"])
async def api_info():
    """API version information"""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "supported_versions": ["v1"],
        "deprecated_versions": [],
        "documentation": "/docs" if settings.DEBUG else None,
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=logging.INFO.lower(),
        access_log=settings.DEBUG,
    )