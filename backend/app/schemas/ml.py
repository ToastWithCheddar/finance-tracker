"""
ML service integration schemas for type-safe communication
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from uuid import UUID

class MLCategorizationRequest(BaseModel):
    """Request schema for ML categorization service"""
    description: str = Field(..., min_length=1, max_length=500, description="Transaction description")
    amount_cents: int = Field(..., description="Transaction amount in cents")
    merchant: Optional[str] = Field(None, max_length=200, description="Merchant name")
    user_id: Optional[str] = Field(None, description="User ID for personalized categorization")
    
    @validator('amount_cents')
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError("Amount cannot be zero")
        return v

class MLCategorizationResponse(BaseModel):
    """Response schema from ML categorization service"""
    category_id: UUID = Field(..., description="Predicted category ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    category_name: Optional[str] = Field(None, description="Predicted category name")
    reasoning: Optional[str] = Field(None, description="Explanation of the prediction")
    alternative_categories: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative category suggestions")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

class MLFeedbackRequest(BaseModel):
    """Request schema for ML feedback/learning"""
    transaction_id: UUID = Field(..., description="Transaction ID")
    description: str = Field(..., description="Transaction description")
    amount_cents: int = Field(..., description="Transaction amount in cents")
    merchant: Optional[str] = Field(None, description="Merchant name")
    correct_category_id: UUID = Field(..., description="Correct category ID")
    predicted_category_id: Optional[UUID] = Field(None, description="Previously predicted category ID")
    confidence: Optional[float] = Field(None, description="Previous prediction confidence")
    user_id: str = Field(..., description="User ID")

class MLFeedbackResponse(BaseModel):
    """Response schema for ML feedback submission"""
    success: bool = Field(..., description="Whether feedback was processed successfully")
    message: str = Field(..., description="Response message")
    model_updated: bool = Field(default=False, description="Whether the model was updated")

class MLHealthResponse(BaseModel):
    """Response schema for ML service health check"""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Service health status")
    version: str = Field(..., description="ML service version")
    model_version: Optional[str] = Field(None, description="Current model version")
    uptime_seconds: Optional[int] = Field(None, description="Service uptime in seconds")
    last_training: Optional[str] = Field(None, description="Last model training timestamp")

class MLBatchCategorizationRequest(BaseModel):
    """Request schema for batch categorization"""
    transactions: List[Dict[str, Any]] = Field(..., min_items=1, max_items=1000, description="List of transactions to categorize")
    user_id: Optional[str] = Field(None, description="User ID for personalized categorization")

class MLBatchCategorizationResponse(BaseModel):
    """Response schema for batch categorization"""
    results: List[MLCategorizationResponse] = Field(..., description="Categorization results")
    processed_count: int = Field(..., description="Number of transactions processed")
    failed_count: int = Field(default=0, description="Number of failed categorizations")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed categorizations")

# Error response schemas
class MLErrorResponse(BaseModel):
    """Standard error response from ML service"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

# Service configuration
class MLServiceConfig(BaseModel):
    """Configuration for ML service integration"""
    base_url: str = Field(..., description="ML service base URL")
    timeout_seconds: float = Field(default=5.0, description="Request timeout in seconds")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for auto-categorization")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    enable_feedback: bool = Field(default=True, description="Whether to enable feedback learning")
    batch_size: int = Field(default=100, description="Maximum batch size for bulk operations")

# Response wrapper for consistent error handling
class MLServiceResponse(BaseModel):
    """Wrapper for ML service responses with metadata"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[MLErrorResponse] = Field(None, description="Error information if request failed")
    request_duration_ms: Optional[int] = Field(None, description="Request duration in milliseconds")
    service_version: Optional[str] = Field(None, description="ML service version")