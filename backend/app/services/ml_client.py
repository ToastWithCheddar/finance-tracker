"""
Type-safe ML service client for transaction categorization
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from ..config import settings
from ..schemas.ml import (
    MLCategorizationRequest,
    MLCategorizationResponse,
    MLFeedbackRequest,
    MLFeedbackResponse,
    MLHealthResponse,
    MLBatchCategorizationRequest,
    MLBatchCategorizationResponse,
    MLErrorResponse,
    MLServiceResponse,
    MLServiceConfig
)

logger = logging.getLogger(__name__)

class MLServiceError(Exception):
    """Custom exception for ML service errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class MLServiceClient:
    """Type-safe client for ML categorization service"""
    
    def __init__(self, config: Optional[MLServiceConfig] = None):
        self.config = config or MLServiceConfig(
            base_url=settings.ML_SERVICE_URL,
            timeout_seconds=getattr(settings, 'ML_TIMEOUT', 5.0),
            confidence_threshold=getattr(settings, 'ML_CONFIDENCE_THRESHOLD', 0.7),
            max_retries=getattr(settings, 'ML_MAX_RETRIES', 3),
            enable_feedback=getattr(settings, 'ML_ENABLE_FEEDBACK', True),
            batch_size=getattr(settings, 'ML_BATCH_SIZE', 100)
        )
        
    async def categorize_transaction(
        self, 
        description: str, 
        amount_cents: int, 
        merchant: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> MLServiceResponse:
        """
        Categorize a single transaction using ML service
        
        Args:
            description: Transaction description
            amount_cents: Transaction amount in cents
            merchant: Optional merchant name
            user_id: Optional user ID for personalized categorization
            
        Returns:
            MLServiceResponse with categorization data or error
        """
        try:
            request_data = MLCategorizationRequest(
                description=description,
                amount_cents=amount_cents,
                merchant=merchant,
                user_id=user_id
            )
            
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    f"{self.config.base_url}/ml/categorize",
                    json=request_data.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Validate response structure
                    categorization_result = MLCategorizationResponse.model_validate(response_data)
                    
                    return MLServiceResponse(
                        success=True,
                        data=categorization_result,
                        request_duration_ms=duration_ms,
                        service_version=response.headers.get("X-Service-Version")
                    )
                else:
                    # Handle error response
                    try:
                        error_data = response.json()
                        error = MLErrorResponse.model_validate(error_data)
                    except Exception:
                        error = MLErrorResponse(
                            error="http_error",
                            message=f"HTTP {response.status_code}: {response.text}"
                        )
                    
                    return MLServiceResponse(
                        success=False,
                        error=error,
                        request_duration_ms=duration_ms
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"ML service timeout after {self.config.timeout_seconds}s")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message=f"ML service request timed out after {self.config.timeout_seconds} seconds"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service request error: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected ML service error: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="unexpected_error",
                    message=f"Unexpected error during categorization: {str(e)}"
                )
            )
    
    async def submit_feedback(
        self,
        transaction_id: UUID,
        description: str,
        amount_cents: int,
        correct_category_id: UUID,
        user_id: str,
        merchant: Optional[str] = None,
        predicted_category_id: Optional[UUID] = None,
        confidence: Optional[float] = None
    ) -> MLServiceResponse:
        """
        Submit feedback to improve ML model
        
        Args:
            transaction_id: Transaction ID
            description: Transaction description
            amount_cents: Transaction amount in cents
            correct_category_id: Correct category ID
            user_id: User ID
            merchant: Optional merchant name
            predicted_category_id: Previously predicted category ID
            confidence: Previous prediction confidence
            
        Returns:
            MLServiceResponse with feedback result
        """
        if not self.config.enable_feedback:
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="feedback_disabled",
                    message="ML feedback is disabled in configuration"
                )
            )
        
        try:
            feedback_data = MLFeedbackRequest(
                transaction_id=transaction_id,
                description=description,
                amount_cents=amount_cents,
                merchant=merchant,
                correct_category_id=correct_category_id,
                predicted_category_id=predicted_category_id,
                confidence=confidence,
                user_id=user_id
            )
            
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    f"{self.config.base_url}/ml/feedback",
                    json=feedback_data.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    feedback_result = MLFeedbackResponse.model_validate(response_data)
                    
                    return MLServiceResponse(
                        success=True,
                        data=feedback_result,
                        request_duration_ms=duration_ms
                    )
                else:
                    try:
                        error_data = response.json()
                        error = MLErrorResponse.model_validate(error_data)
                    except Exception:
                        error = MLErrorResponse(
                            error="http_error",
                            message=f"HTTP {response.status_code}: {response.text}"
                        )
                    
                    return MLServiceResponse(
                        success=False,
                        error=error,
                        request_duration_ms=duration_ms
                    )
                    
        except Exception as e:
            logger.error(f"Error submitting ML feedback: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="feedback_error",
                    message=f"Failed to submit feedback: {str(e)}"
                )
            )
    
    async def batch_categorize(
        self, 
        transactions: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> MLServiceResponse:
        """
        Categorize multiple transactions in batch
        
        Args:
            transactions: List of transaction data
            user_id: Optional user ID for personalized categorization
            
        Returns:
            MLServiceResponse with batch categorization results
        """
        try:
            # Validate batch size
            if len(transactions) > self.config.batch_size:
                return MLServiceResponse(
                    success=False,
                    error=MLErrorResponse(
                        error="batch_too_large",
                        message=f"Batch size {len(transactions)} exceeds maximum {self.config.batch_size}"
                    )
                )
            
            batch_request = MLBatchCategorizationRequest(
                transactions=transactions,
                user_id=user_id
            )
            
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds * 2) as client:  # Double timeout for batch
                response = await client.post(
                    f"{self.config.base_url}/ml/batch-categorize",
                    json=batch_request.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    batch_result = MLBatchCategorizationResponse.model_validate(response_data)
                    
                    return MLServiceResponse(
                        success=True,
                        data=batch_result,
                        request_duration_ms=duration_ms
                    )
                else:
                    try:
                        error_data = response.json()
                        error = MLErrorResponse.model_validate(error_data)
                    except Exception:
                        error = MLErrorResponse(
                            error="http_error",
                            message=f"HTTP {response.status_code}: {response.text}"
                        )
                    
                    return MLServiceResponse(
                        success=False,
                        error=error,
                        request_duration_ms=duration_ms
                    )
                    
        except Exception as e:
            logger.error(f"Error in batch categorization: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="batch_error",
                    message=f"Batch categorization failed: {str(e)}"
                )
            )
    
    async def health_check(self) -> MLServiceResponse:
        """
        Check ML service health
        
        Returns:
            MLServiceResponse with health status
        """
        try:
            start_time = datetime.utcnow()
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.base_url}/health")
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    health_result = MLHealthResponse.model_validate(response_data)
                    
                    return MLServiceResponse(
                        success=True,
                        data=health_result,
                        request_duration_ms=duration_ms
                    )
                else:
                    return MLServiceResponse(
                        success=False,
                        error=MLErrorResponse(
                            error="health_check_failed",
                            message=f"Health check failed with status {response.status_code}"
                        ),
                        request_duration_ms=duration_ms
                    )
                    
        except Exception as e:
            logger.error(f"ML service health check failed: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="health_check_error",
                    message=f"Health check error: {str(e)}"
                )
            )

# Global ML client instance
_ml_client: Optional[MLServiceClient] = None

def get_ml_client() -> MLServiceClient:
    """Get the global ML client instance"""
    global _ml_client
    if _ml_client is None:
        _ml_client = MLServiceClient()
    return _ml_client