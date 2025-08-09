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
from app.routes import auth, user, health, categories, transaction, budget, mlcategory, mock, accounts
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
    logger.info(f"Mock Data Mode: {settings.USE_MOCK_DATA}")
    logger.info(f"UI Only Mode: {settings.UI_ONLY_MODE}")
    logger.info(f"Database Enabled: {settings.ENABLE_DATABASE}")
    
    # Skip database setup if disabled or in mock mode
    if not settings.ENABLE_DATABASE or settings.UI_ONLY_MODE:
        logger.info("⚠️ Database setup skipped (disabled or mock mode)")
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
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return await http_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler"""
    logger.error(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation error",
            "status_code": 422,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
            "details": exc.errors(),
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": str(exc),  # Always show detailed errors in development
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        }
    )

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
    user.router,
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
    transaction.router,
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
    accounts.router,
    prefix="/api/accounts",
    tags=["Accounts & Plaid Integration"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
    }
)

app.include_router(
    mlcategory.router,
    prefix="/api/ml",
    tags=["Machine Learning"],
    responses={
        422: {"description": "Validation Error"},
    }
)

# Mock API routes (for UI development)
app.include_router(
    mock.router,
    prefix="/api/mock",
    tags=["Mock API (Development)"],
    responses={
        404: {"description": "Mock mode disabled"},
    }
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
            "accounts": "/api/accounts",
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