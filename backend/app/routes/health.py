from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import logging
from typing import Dict, Any
from datetime import datetime

from app.database import get_db, check_database_health
from app.config import settings
from app.auth.supabase_client import supabase_client

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def basic_health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "finance-tracker-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check including all services"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "supabase": {"status": "unknown"}
        }
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Supabase
    try:
        if supabase_client.is_configured():
            health_status["checks"]["supabase"] = {"status": "healthy"}
        else:
            health_status["checks"]["supabase"] = {"status": "not_configured"}
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        health_status["checks"]["supabase"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get("/health/database")
async def database_health_check(db: Session = Depends(get_db)):
    """Database-specific health check"""
    try:
        # Test basic query
        result = db.execute(text("SELECT COUNT(*) as count FROM categories WHERE is_system = true"))
        count = result.scalar()
        
        # Test user table
        user_count = db.execute(text("SELECT COUNT(*) as count FROM users")).scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "system_categories": count,
            "total_users": user_count
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail={"status": "unhealthy", "error": str(e)}
        )

@router.get("/health/auth")
async def auth_health_check():
    """Authentication service health check"""
    return {
        "status": "healthy" if supabase_client.is_configured() else "not_configured",
        "supabase_configured": supabase_client.is_configured(),
        "service": "authentication"
    }