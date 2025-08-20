"""
Merchant Recognition and Normalization Service (Think aobut it later)

This service handles the recognition and normalization of merchant names from 
transaction descriptions. It includes pattern matching, fuzzy matching, and 
a learning system for user corrections.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import difflib
from cachetools import TTLCache

from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class MerchantRecognitionResult:
    """Result of merchant recognition"""
    original_description: str
    recognized_merchant: Optional[str]
    confidence_score: float  # 0.0 to 1.0
    method_used: str  # "pattern", "fuzzy", "database", "none"
    suggestions: List[str]  # Alternative merchant names

class MerchantService:
    """Service for merchant recognition and normalization"""
    
    def __init__(self):
        # Common merchant patterns (regex patterns -> clean merchant name)
        self.merchant_patterns = {
            # Square merchants
            r'SQ\s*\*\s*(.+?)(?:\s+\d{3,4})?$': lambda m: m.group(1).title(),
            
            # Amazon variants
            r'AMZN\s*MKTP\s*US\*?(.*)': 'Amazon',
            r'AMZ\*(.*)': 'Amazon',
            r'AMAZON\.?COM\*?(.*)': 'Amazon',
            
            # Common payment processors
            r'PAYPAL\s*\*\s*(.+)': lambda m: m.group(1).title(),
            r'PP\*\s*(.+)': lambda m: m.group(1).title(),
            
            # Walmart variants
            r'WALMART\.?COM\*?(.*)': 'Walmart',
            r'WM\s+SUPERCENTER\s*(.*)': 'Walmart',
            
            # Target variants
            r'TARGET\.?COM\*?(.*)': 'Target',
            r'TARGET\s+T-?\d+': 'Target',
            
            # Starbucks variants
            r'STARBUCKS\s*(?:STORE\s*)?(?:#?\d+)?(.*)': 'Starbucks',
            r'SBUX\s*(.*)': 'Starbucks',
            
            # Gas stations
            r'SHELL\s+OIL\s*(.*)': 'Shell',
            r'EXXONMOBIL\s*(.*)': 'ExxonMobil',
            r'CHEVRON\s*(.*)': 'Chevron',
            r'BP#\d+\s*(.*)': 'BP',
            
            # Food delivery
            r'DOORDASH\*(.+)': 'DoorDash',
            r'UBER\s*EATS\s*(.*)': 'Uber Eats',
            r'GRUBHUB\*(.+)': 'Grubhub',
            
            # Subscription services
            r'SPOTIFY\s*(.*)': 'Spotify',
            r'NETFLIX\.?COM\s*(.*)': 'Netflix',
            r'APPLE\.?COM/BILL\s*(.*)': 'Apple',
            r'GOOGLE\s*\*(.+)': 'Google',
            
            # Utilities
            r'ATT\*BILL\s*(.*)': 'AT&T',
            r'VERIZON\s*(.*)': 'Verizon',
            r'COMCAST\s*(.*)': 'Comcast',
            
            # Banking
            r'CHASE\s+CREDIT\s+CRD\s*(.*)': 'Chase',
            r'WELLS\s+FARGO\s*(.*)': 'Wells Fargo',
            r'BANK\s+OF\s+AMERICA\s*(.*)': 'Bank of America',
            
            # Generic patterns for cleaning
            r'(.+?)\s+#\d+.*': lambda m: m.group(1).title(),  # Remove store numbers
            r'(.+?)\s+\d{3,4}\s*$': lambda m: m.group(1).title(),  # Remove trailing numbers
            r'(.+?)\s+[A-Z]{2}\s*$': lambda m: m.group(1).title(),  # Remove state codes
        }
        
        # Common words to remove/normalize
        self.stop_words = {
            'inc', 'llc', 'ltd', 'corp', 'co', 'company', 'the', 'store', 'shop',
            'market', 'center', 'centre', 'retail', 'online', 'digital', 'services'
        }
        
        # Cache for recognized merchants with TTL to prevent memory leaks
        self._merchant_cache: TTLCache[str, MerchantRecognitionResult] = TTLCache(
            maxsize=settings.MERCHANT_CACHE_MAX_SIZE,
            ttl=settings.MERCHANT_CACHE_TTL
        )
        
        # User corrections storage with TTL cache
        self._user_corrections: TTLCache[str, str] = TTLCache(
            maxsize=settings.MERCHANT_CACHE_MAX_SIZE // 2,  # Smaller cache for corrections
            ttl=settings.MERCHANT_CACHE_TTL * 2  # Longer TTL for user corrections
        )
        
    def recognize_merchant(self, description: str) -> MerchantRecognitionResult:
        """
        Recognize and normalize merchant name from transaction description
        
        Args:
            description: Raw transaction description
            
        Returns:
            MerchantRecognitionResult with recognized merchant and metadata
        """
        if not description or not description.strip():
            return MerchantRecognitionResult(
                original_description=description,
                recognized_merchant=None,
                confidence_score=0.0,
                method_used="none",
                suggestions=[]
            )
        
        # Check cache first
        cache_key = description.strip().upper()
        if cache_key in self._merchant_cache:
            return self._merchant_cache[cache_key]
        
        # Check user corrections first (highest priority)
        if cache_key in self._user_corrections:
            result = MerchantRecognitionResult(
                original_description=description,
                recognized_merchant=self._user_corrections[cache_key],
                confidence_score=1.0,
                method_used="user_correction",
                suggestions=[]
            )
            self._merchant_cache[cache_key] = result
            return result
        
        # Try pattern matching
        result = self._try_pattern_matching(description)
        if result.recognized_merchant and result.confidence_score > 0.7:
            self._merchant_cache[cache_key] = result
            return result
        
        # Try fuzzy matching with known merchants
        fuzzy_result = self._try_fuzzy_matching(description)
        if fuzzy_result.confidence_score > result.confidence_score:
            result = fuzzy_result
        
        # Try simple normalization if no good match found
        if result.confidence_score < 0.5:
            normalized = self._simple_normalization(description)
            if normalized and normalized != description:
                result = MerchantRecognitionResult(
                    original_description=description,
                    recognized_merchant=normalized,
                    confidence_score=0.6,
                    method_used="normalization",
                    suggestions=[]
                )
        
        # Cache result
        self._merchant_cache[cache_key] = result
        return result
    
    def _try_pattern_matching(self, description: str) -> MerchantRecognitionResult:
        """Try to match description against known patterns"""
        clean_desc = description.strip().upper()
        
        for pattern, replacement in self.merchant_patterns.items():
            match = re.search(pattern, clean_desc, re.IGNORECASE)
            if match:
                try:
                    if callable(replacement):
                        merchant_name = replacement(match)
                    else:
                        merchant_name = replacement
                    
                    return MerchantRecognitionResult(
                        original_description=description,
                        recognized_merchant=merchant_name,
                        confidence_score=0.9,
                        method_used="pattern",
                        suggestions=[]
                    )
                except Exception as e:
                    logger.warning(f"Error applying pattern {pattern}: {e}")
                    continue
        
        return MerchantRecognitionResult(
            original_description=description,
            recognized_merchant=None,
            confidence_score=0.0,
            method_used="pattern",
            suggestions=[]
        )
    
    def _try_fuzzy_matching(self, description: str) -> MerchantRecognitionResult:
        """Try fuzzy matching against known merchant names"""
        # Get known merchants from patterns
        known_merchants = set()
        for replacement in self.merchant_patterns.values():
            if isinstance(replacement, str):
                known_merchants.add(replacement.upper())
        
        # Add some common merchants not in patterns
        known_merchants.update([
            'MCDONALDS', 'BURGER KING', 'TACO BELL', 'SUBWAY', 'KFC',
            'COSTCO', 'SAMS CLUB', 'HOME DEPOT', 'LOWES', 'BEST BUY',
            'APPLE', 'MICROSOFT', 'ADOBE', 'DROPBOX', 'SLACK'
        ])
        
        clean_desc = self._clean_for_fuzzy_match(description)
        
        # Find best fuzzy matches
        matches = difflib.get_close_matches(
            clean_desc.upper(), 
            known_merchants, 
            n=3, 
            cutoff=0.6
        )
        
        if matches:
            best_match = matches[0]
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(None, clean_desc.upper(), best_match).ratio()
            
            return MerchantRecognitionResult(
                original_description=description,
                recognized_merchant=best_match.title(),
                confidence_score=similarity,
                method_used="fuzzy",
                suggestions=[m.title() for m in matches[1:]]
            )
        
        return MerchantRecognitionResult(
            original_description=description,
            recognized_merchant=None,
            confidence_score=0.0,
            method_used="fuzzy",
            suggestions=[]
        )
    
    def _clean_for_fuzzy_match(self, description: str) -> str:
        """Clean description for fuzzy matching"""
        # Remove common prefixes/suffixes
        clean = re.sub(r'^(TST\*|SQ\*|PP\*|PAYPAL\*)', '', description, flags=re.IGNORECASE)
        clean = re.sub(r'\*.*$', '', clean)  # Remove everything after *
        clean = re.sub(r'#\d+.*$', '', clean)  # Remove store numbers
        clean = re.sub(r'\d{3,}.*$', '', clean)  # Remove long numbers
        clean = re.sub(r'[^\w\s]', ' ', clean)  # Remove special chars
        clean = re.sub(r'\s+', ' ', clean)  # Normalize whitespace
        
        return clean.strip()
    
    def _simple_normalization(self, description: str) -> Optional[str]:
        """Simple normalization for unrecognized merchants"""
        # Remove common transaction prefixes
        clean = re.sub(r'^(TST\*|SQ\*|PP\*|PAYPAL\*|POS\s+)', '', description, flags=re.IGNORECASE)
        
        # Remove transaction IDs and reference numbers
        clean = re.sub(r'\s+\d{6,}.*$', '', clean)  # Remove long numbers at end
        clean = re.sub(r'#\d+.*$', '', clean)  # Remove store numbers
        clean = re.sub(r'\*\d+.*$', '', clean)  # Remove reference numbers
        
        # Remove common suffixes
        clean = re.sub(r'\s+(INC|LLC|LTD|CORP|CO)\.?$', '', clean, flags=re.IGNORECASE)
        
        # Remove extra whitespace and special chars
        clean = re.sub(r'[^\w\s]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean)
        clean = clean.strip()
        
        # Title case
        words = clean.split()
        if words:
            # Filter out stop words but keep at least one word
            filtered_words = [w for w in words if w.lower() not in self.stop_words]
            if filtered_words:
                words = filtered_words
            
            # Title case each word
            clean = ' '.join(word.title() for word in words)
            
            # Only return if it's actually different and meaningful
            if clean and clean != description and len(clean) >= 3:
                return clean
        
        return None
    
    def add_user_correction(self, original_description: str, corrected_merchant: str) -> None:
        """
        Add a user correction to improve future recognition
        
        Args:
            original_description: Original transaction description
            corrected_merchant: User-provided correct merchant name
        """
        cache_key = original_description.strip().upper()
        self._user_corrections[cache_key] = corrected_merchant
        
        # Update cache
        self._merchant_cache[cache_key] = MerchantRecognitionResult(
            original_description=original_description,
            recognized_merchant=corrected_merchant,
            confidence_score=1.0,
            method_used="user_correction",
            suggestions=[]
        )
        
        logger.info(f"Added user correction: '{original_description}' -> '{corrected_merchant}'")
    
    def get_merchant_suggestions(self, partial_name: str, limit: int = 5) -> List[str]:
        """
        Get merchant suggestions for autocomplete
        
        Args:
            partial_name: Partial merchant name
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested merchant names
        """
        suggestions = set()
        
        # Get suggestions from known patterns
        for replacement in self.merchant_patterns.values():
            if isinstance(replacement, str):
                if partial_name.lower() in replacement.lower():
                    suggestions.add(replacement)
        
        # Get suggestions from user corrections
        for merchant in self._user_corrections.values():
            if partial_name.lower() in merchant.lower():
                suggestions.add(merchant)
        
        # Convert to sorted list
        suggestions_list = sorted(list(suggestions))
        return suggestions_list[:limit]
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear the merchant recognition cache"""
        cache_cleared = len(self._merchant_cache)
        corrections_cleared = len(self._user_corrections)
        
        self._merchant_cache.clear()
        self._user_corrections.clear()
        
        logger.info(f"Merchant cache cleared: {cache_cleared} entries, {corrections_cleared} user corrections")
        return {
            'success': True,
            'cache_entries_cleared': cache_cleared,
            'corrections_cleared': corrections_cleared,
            'message': f'Cleared {cache_cleared} cache entries and {corrections_cleared} user corrections'
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            "cache_size": len(self._merchant_cache),
            "cache_max_size": self._merchant_cache.maxsize,
            "cache_ttl_seconds": self._merchant_cache.ttl,
            "user_corrections": len(self._user_corrections),
            "corrections_max_size": self._user_corrections.maxsize,
            "corrections_ttl_seconds": self._user_corrections.ttl,
            "pattern_count": len(self.merchant_patterns)
        }
    
    def bulk_recognize_merchants(self, descriptions: List[str]) -> List[MerchantRecognitionResult]:
        """
        Recognize merchants for multiple descriptions efficiently
        
        Args:
            descriptions: List of transaction descriptions
            
        Returns:
            List of recognition results in same order
        """
        results = []
        for description in descriptions:
            result = self.recognize_merchant(description)
            results.append(result)
        
        return results

# Global instance
merchant_service = MerchantService()