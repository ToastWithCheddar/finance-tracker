"""
Merchant API Routes

Provides endpoints for merchant recognition, enrichment, and user corrections.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from app.dependencies import get_transaction_service, get_merchant_service
from ..services.merchant_service import merchant_service, MerchantRecognitionResult
from ..services.transaction_service import TransactionService
from app.auth.dependencies import get_current_user, get_db_with_user_context
from ..models.user import User
from ..models.transaction import Transaction
from ..core.exceptions import (
    ExternalServiceError,
    TransactionNotFoundError,
    DataIntegrityError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchants", tags=["merchants"])

# Request/Response Models

class MerchantEnrichmentRequest(BaseModel):
    """Request to enrich a transaction with merchant data"""
    description: Optional[str] = Field(None, description="Override description for recognition")

class MerchantCorrectionRequest(BaseModel):
    """Request to correct merchant recognition"""
    merchant_name: str = Field(..., min_length=1, max_length=200, description="Correct merchant name")

class MerchantRecognitionResponse(BaseModel):
    """Response for merchant recognition"""
    original_description: str
    recognized_merchant: Optional[str]
    confidence_score: float
    method_used: str
    suggestions: List[str]

class MerchantSuggestionResponse(BaseModel):
    """Response for merchant suggestions"""
    suggestions: List[str]

class TransactionEnrichmentResponse(BaseModel):
    """Response for transaction enrichment with merchant data"""
    transaction_id: str
    original_description: str
    recognized_merchant: Optional[str]
    confidence_score: float
    method_used: str
    updated: bool  # Whether transaction was actually updated

# API Endpoints

@router.post("/recognize", response_model=MerchantRecognitionResponse)
def recognize_merchant_from_description(
    description: str = Query(..., min_length=1, description="Transaction description to analyze"),
    current_user: User = Depends(get_current_user)
) -> MerchantRecognitionResponse:
    """
    Recognize merchant from transaction description without updating any transaction
    """
    try:
        result = merchant_service.recognize_merchant(description)
        
        return MerchantRecognitionResponse(
            original_description=result.original_description,
            recognized_merchant=result.recognized_merchant,
            confidence_score=result.confidence_score,
            method_used=result.method_used,
            suggestions=result.suggestions
        )
    except Exception as e:
        logger.error(f"Error recognizing merchant from description '{description}': {str(e)}", exc_info=True)
        raise ExternalServiceError("Merchant Service", "Failed to recognize merchant")

@router.post("/transactions/{transaction_id}/enrich", response_model=TransactionEnrichmentResponse)
def enrich_transaction_with_merchant(
    transaction_id: UUID,
    request: MerchantEnrichmentRequest = MerchantEnrichmentRequest(),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionEnrichmentResponse:
    """
    Enrich a specific transaction with merchant recognition
    """
    try:
        # Get the transaction
        transaction = transaction_service.get_transaction(db, transaction_id, current_user.id)
        if not transaction:
            raise TransactionNotFoundError(str(transaction_id))
        
        # Use provided description or transaction's description
        description_to_analyze = request.description or transaction.description
        
        # Recognize merchant
        result = merchant_service.recognize_merchant(description_to_analyze)
        
        # Update transaction if merchant was recognized and is different
        updated = False
        if (result.recognized_merchant and 
            result.confidence_score >= 0.6 and  # Only update if confidence is decent
            result.recognized_merchant != transaction.merchant):
            
            try:
                # Update the transaction with recognized merchant
                from ..schemas.transaction import TransactionUpdate
                update_data = TransactionUpdate(merchant=result.recognized_merchant)
                transaction_service.update_transaction(db, transaction, update_data)
                updated = True
                
                logger.info(f"Updated transaction {transaction_id} merchant: '{transaction.merchant}' -> '{result.recognized_merchant}'")
            except Exception as e:
                logger.error(f"Failed to update transaction {transaction_id} with merchant: {str(e)}")
                # Continue anyway, just don't mark as updated
        
        return TransactionEnrichmentResponse(
            transaction_id=str(transaction_id),
            original_description=description_to_analyze,
            recognized_merchant=result.recognized_merchant,
            confidence_score=result.confidence_score,
            method_used=result.method_used,
            updated=updated
        )
        
    except TransactionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error enriching transaction {transaction_id}: {str(e)}", exc_info=True)
        raise DataIntegrityError("Failed to enrich transaction with merchant data")

@router.put("/transactions/{transaction_id}/correct", response_model=dict)
def correct_transaction_merchant(
    transaction_id: UUID,
    request: MerchantCorrectionRequest,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> dict:
    """
    Correct the merchant for a transaction and improve recognition system
    """
    try:
        # Get the transaction
        transaction = transaction_service.get_transaction(db, transaction_id, current_user.id)
        if not transaction:
            raise TransactionNotFoundError(str(transaction_id))
        
        # Update the transaction with corrected merchant
        from ..schemas.transaction import TransactionUpdate
        update_data = TransactionUpdate(merchant=request.merchant_name)
        updated_transaction = transaction_service.update_transaction(db, transaction, update_data)
        
        # Add user correction to merchant service to improve future recognition
        merchant_service.add_user_correction(
            original_description=transaction.description,
            corrected_merchant=request.merchant_name
        )
        
        logger.info(f"Corrected transaction {transaction_id} merchant to '{request.merchant_name}' and updated recognition system")
        
        return {
            "message": "Merchant corrected successfully",
            "transaction_id": str(transaction_id),
            "corrected_merchant": request.merchant_name,
            "learning_updated": True
        }
        
    except TransactionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error correcting merchant for transaction {transaction_id}: {str(e)}", exc_info=True)
        raise DataIntegrityError("Failed to correct merchant")

@router.get("/suggestions", response_model=MerchantSuggestionResponse)
def get_merchant_suggestions(
    query: str = Query(..., min_length=1, description="Partial merchant name for autocomplete"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions"),
    current_user: User = Depends(get_current_user)
) -> MerchantSuggestionResponse:
    """
    Get merchant suggestions for autocomplete
    """
    try:
        suggestions = merchant_service.get_merchant_suggestions(query, limit)
        
        return MerchantSuggestionResponse(suggestions=suggestions)
        
    except Exception as e:
        logger.error(f"Error getting merchant suggestions for query '{query}': {str(e)}", exc_info=True)
        raise ExternalServiceError("Merchant Service", "Failed to get merchant suggestions")

@router.post("/bulk-recognize", response_model=List[MerchantRecognitionResponse])
def bulk_recognize_merchants(
    descriptions: List[str] = Field(..., min_items=1, max_items=100, description="List of descriptions to analyze"),
    current_user: User = Depends(get_current_user)
) -> List[MerchantRecognitionResponse]:
    """
    Recognize merchants for multiple descriptions at once
    """
    try:
        results = merchant_service.bulk_recognize_merchants(descriptions)
        
        return [
            MerchantRecognitionResponse(
                original_description=result.original_description,
                recognized_merchant=result.recognized_merchant,
                confidence_score=result.confidence_score,
                method_used=result.method_used,
                suggestions=result.suggestions
            )
            for result in results
        ]
        
    except Exception as e:
        logger.error(f"Error in bulk merchant recognition: {str(e)}", exc_info=True)
        raise ExternalServiceError("Merchant Service", "Failed to perform bulk merchant recognition")

@router.get("/stats", response_model=dict)
def get_merchant_service_stats(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get merchant service statistics (for debugging/monitoring)
    """
    try:
        stats = merchant_service.get_cache_stats()
        
        return {
            "cache_stats": stats,
            "service_status": "active"
        }
        
    except Exception as e:
        logger.error(f"Error getting merchant service stats: {str(e)}", exc_info=True)
        raise ExternalServiceError("Merchant Service", "Failed to get service statistics")

@router.delete("/cache", response_model=dict)
def clear_merchant_cache(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Clear merchant recognition cache (admin function)
    """
    try:
        merchant_service.clear_cache()
        
        return {
            "message": "Merchant recognition cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Error clearing merchant cache: {str(e)}", exc_info=True)
        raise ExternalServiceError("Merchant Service", "Failed to clear cache")