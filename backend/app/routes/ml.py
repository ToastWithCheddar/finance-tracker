"""
ML service integration routes for transaction categorization
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from ..database import get_db
from ..auth.dependencies import get_current_user, get_db_with_user_context
from ..models.user import User
from ..services.transaction_service import TransactionService
from ..services.ml_client import get_ml_client
from ..schemas.ml import (
    MLCategorizationRequest,
    MLCategorizationResponse,
    MLFeedbackRequest,
    MLHealthResponse,
    MLServiceResponse,
    MCategoryExampleRequest,
    MLModelPerformanceResponse,
    MLModelExportResponse,
    MLBatchCategorizationRequest
)

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
    ml_client = get_ml_client()
    
    try:
        response = await ml_client.categorize_transaction(
            description=request.description,
            amount_cents=request.amount_cents,
            merchant=request.merchant,
            user_id=str(current_user.id)
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data.model_dump(),
                "duration_ms": response.request_duration_ms
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": response.error.error,
                    "message": response.error.message,
                    "details": response.error.details
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Categorization failed: {str(e)}"
        )

@router.post("/feedback")
async def submit_feedback(
    transaction_id: UUID,
    correct_category_id: UUID,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback for ML model improvement when user corrects a category
    """
    try:
        success = await TransactionService.submit_ml_feedback(
            db=db,
            transaction_id=transaction_id,
            correct_category_id=correct_category_id,
            user_id=current_user.id
        )
        
        if success:
            return {
                "success": True,
                "message": "Feedback submitted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to submit feedback. Transaction not found or already processed."
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback submission failed: {str(e)}"
        )

@router.get("/health", response_model=Dict[str, Any])
async def ml_service_health():
    """
    Check ML service health status
    """
    ml_client = get_ml_client()
    
    try:
        response = await ml_client.health_check()
        
        return {
            "success": response.success,
            "data": response.data.model_dump() if response.data else None,
            "error": response.error.model_dump() if response.error else None,
            "duration_ms": response.request_duration_ms
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": {
                "error": "health_check_failed",
                "message": f"Health check failed: {str(e)}"
            }
        }

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
        from ..models.transaction import Transaction
        
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
        
        # Count feedback submissions
        feedback_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.user_id == current_user.id,
                Transaction.metadata_json.op('->>')('ml_feedback_submitted') == 'true'
            )
        ).scalar()
        
        return {
            "ml_predicted_transactions": ml_predicted_count,
            "high_confidence_predictions": high_confidence_count,
            "feedback_submissions": feedback_count,
            "accuracy_rate": round((high_confidence_count / max(ml_predicted_count, 1)) * 100, 2)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ML stats: {str(e)}"
        )

@router.post("/batch-categorize", response_model=Dict[str, Any])
async def batch_categorize_transactions(
    request: MLBatchCategorizationRequest,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Categorize multiple transactions in batch
    """
    ml_client = get_ml_client()
    
    try:
        response = await ml_client.batch_categorize(
            transactions=request.transactions,
            user_id=str(current_user.id)
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data.model_dump(),
                "duration_ms": response.request_duration_ms
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": response.error.error,
                    "message": response.error.message,
                    "details": response.error.details
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch categorization failed: {str(e)}"
        )

@router.post("/add-example", status_code=status.HTTP_201_CREATED)
async def add_ml_example(
    request: MCategoryExampleRequest,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new example to a category for improved classification
    """
    ml_client = get_ml_client()
    
    try:
        response = await ml_client.add_training_example(
            category=request.category,
            example=request.example,
            user_id=str(current_user.id)
        )
        
        if response.success:
            return {
                "success": True,
                "message": "Example added successfully",
                "data": response.data,
                "duration_ms": response.request_duration_ms
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": response.error.error,
                    "message": response.error.message,
                    "details": response.error.details
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add example: {str(e)}"
        )

@router.post("/export-model", response_model=Dict[str, Any])
async def export_model(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Export the current model to ONNX format with quantization
    """
    ml_client = get_ml_client()
    
    try:
        response = await ml_client.export_model()
        
        if response.success:
            return {
                "success": True,
                "data": response.data.model_dump(),
                "duration_ms": response.request_duration_ms
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": response.error.error,
                    "message": response.error.message,
                    "details": response.error.details
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export model: {str(e)}"
        )

@router.get("/performance", response_model=Dict[str, Any])
async def get_ml_performance(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """
    Get current model performance metrics
    """
    ml_client = get_ml_client()
    
    try:
        response = await ml_client.get_model_performance()
        
        if response.success:
            return {
                "success": True,
                "data": response.data.model_dump(),
                "duration_ms": response.request_duration_ms
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": response.error.error,
                    "message": response.error.message,
                    "details": response.error.details
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )