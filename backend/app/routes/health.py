from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import logging
from typing import Dict, Any
from datetime import datetime

from app.database import get_db, check_database_health
from app.config import settings
from app.auth.supabase_client import supabase_client
from app.core.exceptions import ExternalServiceError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check(detailed: bool = False, db: Session = Depends(get_db)):
    """Health check endpoint with optional detailed information"""
    health_status = {
        "status": "healthy",
        "service": "finance-tracker-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Return basic health if detailed is False
    if not detailed:
        return health_status
    
    # Add detailed checks
    health_status["checks"] = {
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
        "supabase": {"status": "unknown"}
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
        raise ExternalServiceError("Health Check", f"Service is unhealthy: {health_status}")
    
    return health_status

