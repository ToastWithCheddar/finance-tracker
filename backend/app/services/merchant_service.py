"""
Merchant service for recognizing merchants from transaction descriptions
"""
import logging
from dataclasses import dataclass
from cachetools import TTLCache

logger = logging.getLogger(__name__)

@dataclass
class MerchantRecognitionResult:
    """Result of merchant recognition"""
    recognized_merchant: str
    confidence_score: float

class MerchantService:
    """Service for merchant recognition and management"""
    
    def __init__(self):
        # Simple cache for merchant corrections/mappings
        self.merchant_cache = TTLCache(maxsize=2000, ttl=3600)  # 1 hour TTL
        
    def recognize_merchant(self, description: str) -> MerchantRecognitionResult:
        """
        Recognize merchant from transaction description
        For now, returns unknown since we don't want to guess
        """
        if not description or not description.strip():
            return MerchantRecognitionResult(
                recognized_merchant="Unknown",
                confidence_score=0.0
            )
        
        # Check cache first for any user corrections
        cache_key = description.strip().lower()
        if cache_key in self.merchant_cache:
            cached_merchant = self.merchant_cache[cache_key]
            return MerchantRecognitionResult(
                recognized_merchant=cached_merchant,
                confidence_score=1.0  # User corrections are 100% confident
            )
        
        # For now, we don't try to guess - just return unknown
        return MerchantRecognitionResult(
            recognized_merchant="Unknown",
            confidence_score=0.0
        )
    
    def add_merchant_correction(self, description: str, correct_merchant: str):
        """Add a user correction for merchant recognition"""
        cache_key = description.strip().lower()
        self.merchant_cache[cache_key] = correct_merchant
        logger.info(f"Added merchant correction: '{description}' -> '{correct_merchant}'")

# Global instance
_merchant_service = None

def get_merchant_service() -> MerchantService:
    """Get the global merchant service instance"""
    global _merchant_service
    if _merchant_service is None:
        _merchant_service = MerchantService()
    return _merchant_service