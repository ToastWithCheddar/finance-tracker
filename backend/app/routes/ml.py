"""
ML service integration routes for transaction categorization
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from uuid import UUID
import logging

from app.database import get_db
from app.auth.dependencies import get_current_user, get_db_with_user_context
from app.models.user import User
from app.services.transaction_service import TransactionService
from app.services.ml_service import get_ml_client
from app.schemas.ml import (
    MLCategorizationRequest,
    MLCategorizationResponse,
    MLHealthResponse,
    MLServiceResponse,
    MCategoryExampleRequest,
    MLModelPerformanceResponse,
    MLModelExportResponse,
    MLBatchCategorizationRequest
)
from app.core.exceptions import (
    MLServiceError,
    ValidationError,
    DataIntegrityError
)
from app.config import settings

from celery import Celery

# Celery client for ML worker tasks (Redis broker)
celery_app = Celery('ml_client', broker=settings.REDIS_URL, backend=settings.REDIS_URL)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])

@router.post("/categorize", response_model=Dict[str, Any])
async def categorize_transaction(
    request: MLCategorizationRequest,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Categorize a single transaction using ML service
    """
    try:
        payload = {
            'id': None,
            'description': request.description,
            # Convert cents to float dollars if present
            'amount': (request.amount_cents / 100.0) if request.amount_cents is not None else None,
            'merchant': request.merchant,
            'user_id': str(current_user.id)
        }
        result_async = celery_app.send_task('worker.classify_transaction', args=[payload])
        result = result_async.get(timeout=30)
        return {
            'success': True,
            'data': {
                'category_id': result.get('predicted_category'),
                'confidence': result.get('confidence'),
                'confidence_level': result.get('confidence_level'),
                'model_version': result.get('model_version'),
                'all_similarities': result.get('all_similarities', {})
            }
        }
    except Exception as celery_error:
        logger.warning(f"Celery ML classify fallback failed: {celery_error}")
        # Fallback to HTTP ML client if available
        ml_client = get_ml_client()
        try:
            response = await ml_client.categorize_transaction(
                description=request.description,
                amount_cents=request.amount_cents,
                merchant=request.merchant,
                user_id=current_user.id
            )
            if response.success:
                return {
                    "success": True,
                    "data": response.data.model_dump(),
                    "duration_ms": response.request_duration_ms
                }
            else:
                raise MLServiceError(f"ML service error: {response.error.message}")
        except Exception as http_error:
            logger.error(f"ML categorization failed: {http_error}", exc_info=True)
            raise MLServiceError("Unable to categorize transaction")


@router.get("/health", response_model=Dict[str, Any])
async def ml_service_health():
    """
    Check ML service health status
    """
    try:
        result = celery_app.send_task('worker.health_check').get(timeout=15)
        return {"success": True, "data": result}
    except Exception as e:
        logger.warning(f"Celery health_check failed: {e}")
        return {"success": False, "error": {"error": "health_check_failed", "message": str(e)}}

@router.get("/stats", response_model=Dict[str, Any])
async def get_ml_stats(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Get ML usage statistics for the current user
    """
    try:
        # Query user's ML-categorized transactions
        from sqlalchemy import func, and_
        from app.models.transaction import Transaction
        
        # Count ML-predicted transactions
        ml_predicted_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.user_id == current_user.id,
                Transaction.ml_suggested_category_id.isnot(None)
            )
        ).scalar()
        
        # Count high-confidence predictions
        high_confidence_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.user_id == current_user.id,
                Transaction.confidence_score >= 0.8
            )
        ).scalar()
        
        return {
            "ml_predicted_transactions": ml_predicted_count,
            "high_confidence_predictions": high_confidence_count,
            "accuracy_rate": round((high_confidence_count / max(ml_predicted_count, 1)) * 100, 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to get ML stats: {e}", exc_info=True)
        raise MLServiceError("Unable to retrieve ML statistics")

@router.post("/batch-categorize", response_model=Dict[str, Any])
async def batch_categorize_transactions(
    request: MLBatchCategorizationRequest,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Categorize multiple transactions in batch
    """
    try:
        # Normalize transactions for worker
        txs: List[Dict[str, Any]] = []
        for t in request.transactions:
            txs.append({
                'id': t.get('id'),
                'description': t.get('description', ''),
                'amount': t.get('amount'),  # Worker ignores amount if unused
                'merchant': t.get('merchant')
            })
        # Dynamic timeout based on batch size - allow more time for larger batches
        batch_size = len(txs)
        timeout = min(300, max(60, batch_size * 2))  # 2 seconds per transaction, min 60s, max 300s
        logger.info(f"Processing batch of {batch_size} transactions with {timeout}s timeout")
        
        result = celery_app.send_task('worker.batch_classify_transactions', args=[txs]).get(timeout=timeout)
        
        # Apply ML categorization results to database
        try:
            update_stats = TransactionService.apply_batch_ml_categorization(
                db=db,
                ml_results=result,
                user_id=current_user.id
            )
            logger.info(f"Applied ML categorization: {update_stats}")
        except Exception as apply_error:
            logger.error(f"Failed to apply ML categorization to database: {apply_error}", exc_info=True)
            # Continue to return results even if database update fails
            update_stats = {
                "updated_count": 0,
                "skipped_count": 0,
                "error_count": len(result),
                "errors": [str(apply_error)]
            }
        
        # Map to frontend-friendly batch response
        mapped = []
        for item in result:
            mapped.append({
                'id': item.get('transaction_id') or item.get('id'),
                'prediction': {
                    'categoryId': item.get('predicted_category'),
                    'confidence': item.get('confidence')
                }
            })
        
        return {
            'success': True,
            'data': {
                'results': mapped,
                'processed_count': len(mapped),
                'failed_count': update_stats.get('error_count', 0),
                'errors': update_stats.get('errors', []),
                'update_stats': update_stats
            }
        }
    except Exception as celery_error:
        logger.error(f"ML batch categorization failed via Celery: {celery_error}", exc_info=True)
        raise MLServiceError("Unable to perform batch categorization")

@router.post("/add-example", status_code=201)
async def add_ml_example(
    request: MCategoryExampleRequest,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new example to a category for improved classification
    """
    try:
        result = celery_app.send_task('worker.add_category_example', args=[request.category, request.example, str(current_user.id)]).get(timeout=30)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Failed to add ML example: {e}", exc_info=True)
        raise MLServiceError("Unable to add training example")

@router.post("/export-model", response_model=Dict[str, Any])
async def export_model(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Export the current model to ONNX format with quantization
    """
    try:
        # Prefer creating production ONNX models
        result = celery_app.send_task('worker.create_onnx_models').get(timeout=600)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Failed to export ML model: {e}", exc_info=True)
        raise MLServiceError("Unable to export model")

@router.get("/performance", response_model=Dict[str, Any])
async def get_ml_performance(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Get current model performance metrics
    """
    try:
        result = celery_app.send_task('worker.get_model_performance').get(timeout=30)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Failed to get ML performance metrics: {e}", exc_info=True)
        raise MLServiceError("Unable to retrieve performance metrics")
