"""
Type-safe ML service client for transaction categorization
"""
import httpx
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import random

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
    MLServiceConfig,
    MCategoryExampleRequest,
    MLModelPerformanceResponse,
    MLModelExportResponse
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
    
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        timeout: float,
        max_retries: Optional[int] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries (defaults to config.max_retries)
            json_data: JSON payload for request
            headers: Request headers
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.RequestError: After all retries are exhausted
        """
        retries = max_retries or self.config.max_retries
        last_exception = None
        
        for attempt in range(retries + 1):  # +1 for initial attempt
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=json_data, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    # Check if we should retry based on status code
                    if response.status_code >= 500 or response.status_code == 429:
                        # Server errors or rate limiting - should retry
                        if attempt < retries:
                            delay = self._calculate_backoff_delay(attempt)
                            logger.warning(
                                f"ML service returned {response.status_code}, retrying in {delay:.2f}s "
                                f"(attempt {attempt + 1}/{retries + 1})"
                            )
                            await asyncio.sleep(delay)
                            continue
                    
                    # Success or non-retryable error
                    return response
                    
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = e
                if attempt < retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(
                        f"ML service request failed ({type(e).__name__}: {str(e)}), "
                        f"retrying in {delay:.2f}s (attempt {attempt + 1}/{retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # All retries exhausted
                    logger.error(
                        f"ML service request failed after {retries + 1} attempts. "
                        f"Last error: {type(e).__name__}: {str(e)}"
                    )
                    raise e
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise httpx.RequestError("All retry attempts failed")
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        base_delay = min(2 ** attempt, 30)  # Cap at 30 seconds
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.1, 0.5)  # 10-50% jitter
        
        return base_delay + jitter
        
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
            
            response = await self._make_request_with_retry(
                method="POST",
                url=f"{self.config.base_url}/ml/categorize",
                timeout=self.config.timeout_seconds,
                json_data=request_data.model_dump(),
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message=f"ML service request timed out after {self.config.max_retries + 1} attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"ML service request failed after {self.config.max_retries + 1} attempts: {str(e)}"
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
            
            response = await self._make_request_with_retry(
                method="POST",
                url=f"{self.config.base_url}/ml/feedback",
                timeout=self.config.timeout_seconds,
                json_data=feedback_data.model_dump(),
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service feedback timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message=f"ML feedback request timed out after {self.config.max_retries + 1} attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service feedback connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service for feedback after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service feedback request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"ML feedback request failed after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected error submitting ML feedback: {str(e)}")
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
            
            response = await self._make_request_with_retry(
                method="POST",
                url=f"{self.config.base_url}/ml/batch-categorize",
                timeout=self.config.timeout_seconds * 2,  # Double timeout for batch
                json_data=batch_request.model_dump(),
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service batch timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message=f"ML batch request timed out after {self.config.max_retries + 1} attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service batch connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service for batch after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service batch request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"ML batch request failed after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in batch categorization: {str(e)}")
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
            
            response = await self._make_request_with_retry(
                method="GET",
                url=f"{self.config.base_url}/health",
                timeout=5.0,
                max_retries=2  # Fewer retries for health checks
            )
            
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service health check timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message="Health check timed out after 3 attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service health check connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service for health check after 3 attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service health check request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"Health check request failed after 3 attempts: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected ML service health check error: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="health_check_error",
                    message=f"Health check error: {str(e)}"
                )
            )
    
    async def add_training_example(self, category: str, example: str, user_id: str) -> MLServiceResponse:
        """
        Add a new training example to a category for improved classification
        
        Args:
            category: Category name
            example: Example text for the category
            user_id: User ID providing the example
            
        Returns:
            MLServiceResponse with operation result
        """
        try:
            request_data = MCategoryExampleRequest(
                category=category,
                example=example
            )
            
            start_time = datetime.utcnow()
            
            response = await self._make_request_with_retry(
                method="POST",
                url=f"{self.config.base_url}/ml/add-example",
                timeout=self.config.timeout_seconds,
                json_data=request_data.model_dump(),
                headers={"Content-Type": "application/json"}
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    
                    return MLServiceResponse(
                        success=True,
                        data=response_data,
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service add example timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message=f"Add example request timed out after {self.config.max_retries + 1} attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service add example connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service for add example after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service add example request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"Add example request failed after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected error adding training example: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="add_example_error",
                    message=f"Failed to add training example: {str(e)}"
                )
            )
    
    async def export_model(self) -> MLServiceResponse:
        """
        Export the current model to ONNX format with quantization
        
        Returns:
            MLServiceResponse with export result
        """
        try:
            start_time = datetime.utcnow()
            
            response = await self._make_request_with_retry(
                method="POST",
                url=f"{self.config.base_url}/ml/export-model",
                timeout=300.0,  # 5 minutes timeout for export
                max_retries=1  # Fewer retries for long-running operations
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    export_result = MLModelExportResponse.model_validate(response_data)
                    
                    return MLServiceResponse(
                        success=True,
                        data=export_result,
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service export timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message="Model export timed out after 2 attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service export connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service for export after 2 attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service export request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"Export request failed after 2 attempts: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected error exporting model: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="export_error",
                    message=f"Failed to export model: {str(e)}"
                )
            )
    
    async def get_model_performance(self) -> MLServiceResponse:
        """
        Get current model performance metrics
        
        Returns:
            MLServiceResponse with performance metrics
        """
        try:
            start_time = datetime.utcnow()
            
            response = await self._make_request_with_retry(
                method="GET",
                url=f"{self.config.base_url}/ml/performance",
                timeout=self.config.timeout_seconds
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    performance_result = MLModelPerformanceResponse.model_validate(response_data)
                    
                    return MLServiceResponse(
                        success=True,
                        data=performance_result,
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
                    
        except httpx.TimeoutException as e:
            logger.error(f"ML service performance timeout after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="timeout",
                    message=f"Performance request timed out after {self.config.max_retries + 1} attempts"
                )
            )
            
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"ML service performance connection error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="connection_error",
                    message=f"Failed to connect to ML service for performance after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except httpx.RequestError as e:
            logger.error(f"ML service performance request error after all retries: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="request_error",
                    message=f"Performance request failed after {self.config.max_retries + 1} attempts: {str(e)}"
                )
            )
            
        except Exception as e:
            logger.error(f"Unexpected error getting model performance: {str(e)}")
            return MLServiceResponse(
                success=False,
                error=MLErrorResponse(
                    error="performance_error",
                    message=f"Failed to get model performance: {str(e)}"
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