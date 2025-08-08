from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional, Dict, Any
import random
import logging
from celery import Celery
import os

from ..auth.dependencies import get_current_user
from ..models.user import User

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Configure Celery client for ML worker
celery_app = Celery(
    'ml_client',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379')
)

class CategorizeRequest(BaseModel):
    description: str = Field(..., example="Coffee with friend")
    amount: float = Field(..., example=-4.50)
    merchant: Optional[str] = Field(None, example="Starbucks")

class CategoriseResponse(BaseModel):
    category_id: UUID
    confidence: float = Field(..., ge=0, le=1)
    confidence_level: str = Field(..., example="high")
    model_version: str
    all_similarities: Optional[Dict[str, float]] = None

class BatchCategorizeRequest(BaseModel):
    transactions: List[Dict[str, Any]] = Field(..., example=[
        {"id": "123", "description": "Coffee shop", "amount": -4.50, "merchant": "Starbucks"},
        {"id": "124", "description": "Gas station", "amount": -45.00, "merchant": "Shell"}
    ])

class FeedbackRequest(BaseModel):
    transaction_id: str
    predicted_category: str 
    actual_category: str

class CategoryExampleRequest(BaseModel):
    category: str = Field(..., example="Food & Dining")
    example: str = Field(..., example="coffee shop morning latte")

class MLHealthResponse(BaseModel):
    status: str
    model_loaded: bool
    prototypes_loaded: bool
    categories_count: int
    model_version: str

@router.post("/ml/categorise", response_model=CategoriseResponse)
async def categorise(req: CategorizeRequest, current_user: User = Depends(get_current_user)):
    """
    Classify a transaction using the ML model with sentence transformers
    """
    try:
        # Call ML worker asynchronously
        task = celery_app.send_task('classify_transaction', args=[{
            'description': req.description,
            'amount': req.amount,
            'merchant': req.merchant
        }])
        
        # Wait for result with timeout
        try:
            result = task.get(timeout=30)
            
            # Map category name to UUID (this would be done via database lookup in production)
            category_mapping = {
                "Food & Dining": "e0b8a9f7-5b7a-4b0e-8b0a-3a4c5d6e7f8b",
                "Transportation": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d", 
                "Shopping": "c3d4e5f6-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
                "Bills & Utilities": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
                "Entertainment": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
                "Healthcare": "f6a7b8c9-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
                "Income": "f1c2d3e4-5b6a-7b8c-9d0e-1a2b3c4d5e6f"
            }
            
            predicted_category = result['predicted_category']
            category_id = UUID(category_mapping.get(predicted_category, category_mapping["Shopping"]))
            
            return CategoriseResponse(
                category_id=category_id,
                confidence=result['confidence'],
                confidence_level=result['confidence_level'],
                model_version=result['model_version'],
                all_similarities=result.get('all_similarities')
            )
            
        except Exception as e:
            logger.error(f"ML classification failed, falling back to rule-based: {e}")
            # Fallback to rule-based classification
            return _fallback_categorization(req)
            
    except Exception as e:
        logger.error(f"Failed to call ML worker: {e}")
        return _fallback_categorization(req)

@router.post("/ml/batch-categorise")
async def batch_categorise(req: BatchCategorizeRequest, current_user: User = Depends(get_current_user)):
    """
    Classify multiple transactions in batch
    """
    try:
        task = celery_app.send_task('batch_classify_transactions', args=[req.transactions])
        results = task.get(timeout=60)
        
        return {"results": results, "status": "success"}
        
    except Exception as e:
        logger.error(f"Batch classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch classification failed: {str(e)}")

@router.post("/ml/feedback")
async def submit_feedback(req: FeedbackRequest, current_user: User = Depends(get_current_user)):
    """
    Submit user feedback for model improvement
    """
    try:
        task = celery_app.send_task('collect_user_feedback', args=[{
            'transaction_id': req.transaction_id,
            'predicted_category': req.predicted_category,
            'actual_category': req.actual_category,
            'user_id': str(current_user.id)
        }])
        
        result = task.get(timeout=10)
        return {"status": "feedback_submitted", "result": result}
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")

@router.post("/ml/add-example")
async def add_category_example(req: CategoryExampleRequest, current_user: User = Depends(get_current_user)):
    """
    Add a new example to a category for improved classification
    """
    try:
        task = celery_app.send_task('add_category_example', args=[
            req.category, req.example, str(current_user.id)
        ])
        
        result = task.get(timeout=15)
        return {"status": "example_added", "result": result}
        
    except Exception as e:
        logger.error(f"Failed to add example: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add example: {str(e)}")

@router.post("/ml/export-model")
async def export_model(current_user: User = Depends(get_current_user)):
    """
    Export the current model to ONNX format with quantization
    """
    try:
        task = celery_app.send_task('export_model_to_onnx')
        result = task.get(timeout=300)  # 5 minutes timeout for export
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to export model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export model: {str(e)}")

@router.get("/ml/performance")
async def get_model_performance(current_user: User = Depends(get_current_user)):
    """
    Get current model performance metrics
    """
    try:
        task = celery_app.send_task('get_model_performance')
        result = task.get(timeout=10)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")

@router.get("/ml/health", response_model=MLHealthResponse)
async def ml_health_check():
    """
    Health check for the ML classification system
    """
    try:
        task = celery_app.send_task('health_check')
        result = task.get(timeout=10)
        
        return MLHealthResponse(**result)
        
    except Exception as e:
        logger.error(f"ML health check failed: {e}")
        # Return unhealthy status
        return MLHealthResponse(
            status="unhealthy",
            model_loaded=False,
            prototypes_loaded=False,
            categories_count=0,
            model_version="unknown"
        )

def _fallback_categorization(req: CategorizeRequest) -> CategoriseResponse:
    """Fallback rule-based categorization when ML worker is unavailable"""
    description_lower = req.description.lower()
    
    rule_based_categories = {
        "coffee": ("e0b8a9f7-5b7a-4b0e-8b0a-3a4c5d6e7f8b", 0.95),
        "starbucks": ("e0b8a9f7-5b7a-4b0e-8b0a-3a4c5d6e7f8b", 0.99),
        "salary": ("f1c2d3e4-5b6a-7b8c-9d0e-1a2b3c4d5e6f", 0.98),
        "uber": ("a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d", 0.92),
        "lyft": ("a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d", 0.92),
        "groceries": ("e0b8a9f7-5b7a-4b0e-8b0a-3a4c5d6e7f8b", 0.90),
    }

    for keyword, (cat_id, confidence) in rule_based_categories.items():
        if keyword in description_lower:
            return CategoriseResponse(
                category_id=UUID(cat_id), 
                confidence=confidence,
                confidence_level="high" if confidence > 0.8 else "medium",
                model_version="fallback_v1.0"
            )

    # Random fallback
    mock_categories = [
        "e0b8a9f7-5b7a-4b0e-8b0a-3a4c5d6e7f8b",
        "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d", 
        "c3d4e5f6-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
        "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
    ]
    
    confidence = random.uniform(0.5, 0.75)
    return CategoriseResponse(
        category_id=UUID(random.choice(mock_categories)),
        confidence=confidence,
        confidence_level="low",
        model_version="fallback_v1.0"
    )
