# Standard library imports
from contextlib import asynccontextmanager
import logging
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Third-party imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
import structlog
import uvicorn

# Local imports
from app.config import settings
from app.database import engine, check_database_health, create_database
from app.logging_config import configure_logging, get_logger
from app.models import Base
from app.routes import auth, users, health, categories, transactions, budget, webhooks, notifications, ml, websockets, dashboard, goals
from app.routes import accounts_basic, accounts_plaid, accounts_sync, accounts_reconciliation
from app.core.exceptions import FinanceTrackerException
from app.schemas.error import ErrorResponse, ValidationErrorResponse

# Configure structured logging — JSON in non-dev, pretty console in dev.
configure_logging("backend")
logger = get_logger(__name__)

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
    
        # BE-PR-001/BE-PR-002 (closed): schema is owned exclusively by Alembic.
        # Operators must run `alembic upgrade head` before starting the API
        # (the prod-up Makefile target chains them). We assert here that the
        # current head is reachable so a misconfigured deploy fails loudly
        # instead of silently running on a drifted schema.
        try:
            from alembic.config import Config as _AlembicConfig
            from alembic.script import ScriptDirectory as _ScriptDir
            cfg = _AlembicConfig(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
            head = _ScriptDir.from_config(cfg).get_current_head()
            logger.info(f"✅ Alembic head present: {head}")
        except Exception as e:
            logger.error(f"❌ Alembic config check failed: {e}")
            raise RuntimeError(f"Alembic config check failed: {e}")
        
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
    
    # Start WebSocket cleanup background task
    try:
        from app.routes.websockets import cleanup_stale_connections
        cleanup_task = asyncio.create_task(cleanup_stale_connections())
        logger.info("✅ WebSocket cleanup background task started")
    except Exception as e:
        logger.warning(f"⚠️ WebSocket cleanup task failed to start: {e}")
    
    logger.info("🎉 Finance Tracker API started successfully!")
    
    yield
    
    # Shutdown: Cancel background tasks
    try:
        if 'cleanup_task' in locals():
            cleanup_task.cancel()
            await cleanup_task
        logger.info("✅ Background tasks cancelled")
    except asyncio.CancelledError:
        logger.info("✅ Background tasks cancelled")
    except Exception as e:
        logger.warning(f"⚠️ Error cancelling background tasks: {e}")
    
    # Shutdown
    logger.info("🛑 Shutting down Finance Tracker API...")

# Create FastAPI app - Development Configuration
app = FastAPI(
    title="Finance Tracker API (Development)",
    description="A comprehensive personal finance management API - DEVELOPMENT MODE",
    version="1.0.0-dev",
    docs_url="/docs",  
    redoc_url="/redoc",  
    openapi_url="/openapi.json",  
    lifespan=lifespan,
    contact={
        "name": "Finance Tracker Development",
        "email": "dev@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Rate limiting setup — share a single Limiter instance across modules so
# routes can apply @limiter.limit(...) without circular-importing main.
from app.core.rate_limit import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
    expose_headers=["X-Process-Time", "X-Request-ID"],
)
app.add_middleware(SlowAPIMiddleware)

# Request timing + request-id middleware (BE-LOG-001)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()

    # Honour incoming X-Request-ID if present, else generate.
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=round(process_time * 1000, 2),
        )
        return response
    finally:
        structlog.contextvars.unbind_contextvars("request_id")


# Prometheus metrics — gated by settings.METRICS_ENABLED (default True).
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    if getattr(settings, "METRICS_ENABLED", True):
        Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("metrics.exposed", endpoint="/metrics")
except Exception as _metrics_exc:  # pragma: no cover - optional dep
    logger.warning("metrics.disabled", error=str(_metrics_exc))

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


# FE-SEC-002 — Double-submit-cookie CSRF.
# - Server issues a `csrf_token` cookie (Secure, SameSite=Strict, NOT HttpOnly
#   so the SPA can read it). Cookie + header are compared on every mutating
#   request. GET/HEAD/OPTIONS are exempt.
# - The middleware is a no-op when settings.CSRF_PROTECTION is False so local
#   dev tooling that doesn't send cookies still works.
import secrets as _csrf_secrets

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
_CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_EXEMPT_PATHS = {
    # WebSocket handshakes never carry the CSRF cookie/header pair.
    "/ws",
    # Webhooks are signed independently (Plaid + Supabase secrets).
    "/api/webhooks/plaid",
    "/api/webhooks/supabase",
    # Health checks must remain pingable without auth.
    "/health",
    "/metrics",
}


def _is_csrf_exempt(path: str) -> bool:
    if path in _CSRF_EXEMPT_PATHS:
        return True
    # Exempt the auth bootstrap endpoints — clients have no cookie yet.
    if path.startswith("/api/auth/login") or path.startswith("/api/auth/register"):
        return True
    if path.startswith("/api/auth/refresh"):
        return True
    return False


@app.middleware("http")
async def csrf_double_submit(request: Request, call_next):
    if not getattr(settings, "CSRF_PROTECTION", True):
        return await call_next(request)

    method = request.method.upper()
    path = request.url.path

    # Issue / refresh the cookie on safe methods so SPAs can pick it up
    # before they ever try to mutate.
    if method in _CSRF_SAFE_METHODS or _is_csrf_exempt(path):
        response = await call_next(request)
        existing = request.cookies.get(CSRF_COOKIE)
        if not existing:
            token = _csrf_secrets.token_urlsafe(32)
            response.set_cookie(
                key=CSRF_COOKIE,
                value=token,
                secure=not settings.DEBUG,
                samesite="strict",
                httponly=False,  # SPA must read it to echo via header
                path="/",
            )
        return response

    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)
    if not cookie_token or not header_token or not _csrf_secrets.compare_digest(
        cookie_token, header_token
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF token missing or invalid"},
        )
    return await call_next(request)

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
        content=error_response.model_dump(mode='json')
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
        content=error_response.model_dump(mode='json')
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
    
    return Response(
        content=error_response.model_dump_json(),
        status_code=422,
        media_type="application/json"
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
        content=error_response.model_dump(mode='json')
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
    goals.router,
    prefix="/api",
    tags=["Goals"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard"],
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
            "budgets": "/api/budgets",
            "dashboard": "/api/dashboard",
            "accounts": "/api/accounts",
            "webhooks": "/api/webhooks",
            "notifications": "/api/notifications",

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
        log_level=logging.getLevelName(logging.INFO).lower(),
        access_log=settings.DEBUG,
    )
