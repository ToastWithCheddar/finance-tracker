# Standard library imports
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
from collections import defaultdict, Counter
import re
from dataclasses import dataclass
import math

# Third-party imports
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

# Local imports
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransactionRule, FrequencyType
from app.models.category import Category
from app.services.base_service import BaseService

@dataclass
class RecurringPattern:
    """Data class representing a detected recurring pattern."""
    merchant: str
    normalized_merchant: str
    amount_cents: int
    amounts: List[int]  # All amounts in the pattern
    transaction_ids: List[UUID]
    dates: List[date]
    frequency: FrequencyType
    interval: int
    confidence_score: float
    category_id: Optional[UUID]
    account_id: UUID
    avg_amount_cents: int
    std_dev_cents: float
    detection_method: str

class RecurringDetectionService(BaseService):
    """Service for detecting recurring transaction patterns."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        
        # Detection parameters
        self.MIN_OCCURRENCES = 3  # Minimum transactions to form a pattern
        self.MAX_ANALYSIS_DAYS = 180  # Look back 6 months
        self.AMOUNT_TOLERANCE_PERCENT = 0.15  # ±15% tolerance for amounts
        self.MIN_AMOUNT_CENTS = 500  # $5.00 minimum for recurring detection
        
        # Frequency tolerances (in days)
        self.FREQUENCY_TOLERANCES = {
            FrequencyType.WEEKLY: 2,      # ±2 days for weekly
            FrequencyType.BIWEEKLY: 3,    # ±3 days for bi-weekly  
            FrequencyType.MONTHLY: 5,     # ±5 days for monthly
            FrequencyType.QUARTERLY: 7,   # ±7 days for quarterly
            FrequencyType.ANNUALLY: 14,   # ±14 days for annual
        }
    
    def detect_patterns_for_user(self, user_id: UUID) -> List[RecurringPattern]:
        """
        Detect all recurring patterns for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of detected RecurringPattern objects
        """
        # Get transactions for analysis
        cutoff_date = date.today() - timedelta(days=self.MAX_ANALYSIS_DAYS)
        
        transactions = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= cutoff_date,
                Transaction.status == 'posted',
                func.abs(Transaction.amount_cents) >= self.MIN_AMOUNT_CENTS
            )
        ).order_by(Transaction.transaction_date).all()
        
        if len(transactions) < self.MIN_OCCURRENCES:
            return []
            
        # Group transactions by normalized merchant
        merchant_groups = self._group_by_merchant(transactions)
        
        patterns = []
        for merchant, merchant_transactions in merchant_groups.items():
            if len(merchant_transactions) < self.MIN_OCCURRENCES:
                continue
                
            # Find patterns within this merchant group
            merchant_patterns = self._detect_patterns_in_group(merchant, merchant_transactions)
            patterns.extend(merchant_patterns)
        
        # Sort by confidence score (highest first)
        patterns.sort(key=lambda p: p.confidence_score, reverse=True)
        
        return patterns
    
    def _group_by_merchant(self, transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
        """Group transactions by normalized merchant name."""
        groups = defaultdict(list)
        
        for transaction in transactions:
            normalized = self._normalize_merchant_name(transaction.description, transaction.merchant)
            groups[normalized].append(transaction)
        
        return groups
    
    def _normalize_merchant_name(self, description: str, merchant: Optional[str] = None) -> str:
        """
        Normalize merchant/description for grouping.
        
        This helps group similar transactions together (e.g., "Netflix.com" and "NETFLIX COM").
        """
        text = merchant or description
        if not text:
            return "unknown"
        
        # Convert to lowercase and remove common patterns
        normalized = text.lower().strip()
        
        # Remove common suffixes/prefixes
        patterns_to_remove = [
            r'\b(www\.)', r'\b(\.com)', r'\b(\.net)', r'\b(\.org)',
            r'\b(inc\.?)', r'\b(llc\.?)', r'\b(corp\.?)', r'\b(ltd\.?)',
            r'\b(payment)', r'\b(autopay)', r'\b(recurring)',
            r'^\*', r'\s+\d+$',  # Remove trailing numbers
            r'\b\d{2}/\d{2}',    # Remove dates
        ]
        
        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, '', normalized)
        
        # Clean up whitespace and special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized or "unknown"
    
    def _detect_patterns_in_group(self, merchant: str, transactions: List[Transaction]) -> List[RecurringPattern]:
        """Detect recurring patterns within a merchant group."""
        if len(transactions) < self.MIN_OCCURRENCES:
            return []
        
        # Sort by date for time-based analysis
        transactions.sort(key=lambda t: t.transaction_date)
        
        # Group by similar amounts (±15% tolerance)
        amount_groups = self._group_by_similar_amounts(transactions)
        
        patterns = []
        for amounts, amount_transactions in amount_groups.items():
            if len(amount_transactions) < self.MIN_OCCURRENCES:
                continue
            
            # Analyze temporal patterns
            pattern = self._analyze_temporal_pattern(merchant, amount_transactions)
            if pattern and pattern.confidence_score > 0.5:  # Minimum confidence threshold
                patterns.append(pattern)
        
        return patterns
    
    def _group_by_similar_amounts(self, transactions: List[Transaction]) -> Dict[Tuple[int, int], List[Transaction]]:
        """Group transactions by similar amounts with tolerance."""
        groups = defaultdict(list)
        processed = set()
        
        for i, transaction in enumerate(transactions):
            if i in processed:
                continue
                
            amount = abs(transaction.amount_cents)
            tolerance = max(int(amount * self.AMOUNT_TOLERANCE_PERCENT), 100)  # Min $1 tolerance
            
            # Find all transactions within tolerance
            similar_transactions = [transaction]
            processed.add(i)
            
            for j, other_transaction in enumerate(transactions[i+1:], i+1):
                if j in processed:
                    continue
                    
                other_amount = abs(other_transaction.amount_cents)
                if abs(amount - other_amount) <= tolerance:
                    similar_transactions.append(other_transaction)
                    processed.add(j)
            
            if len(similar_transactions) >= self.MIN_OCCURRENCES:
                # Use average amount as the key
                avg_amount = int(sum(abs(t.amount_cents) for t in similar_transactions) / len(similar_transactions))
                groups[(avg_amount, tolerance)] = similar_transactions
        
        return groups
    
    def _analyze_temporal_pattern(self, merchant: str, transactions: List[Transaction]) -> Optional[RecurringPattern]:
        """Analyze the temporal pattern of transactions to determine frequency."""
        if len(transactions) < self.MIN_OCCURRENCES:
            return None
        
        # Sort by date
        transactions.sort(key=lambda t: t.transaction_date)
        dates = [t.transaction_date for t in transactions]
        
        # Calculate intervals between consecutive transactions
        intervals = []
        for i in range(1, len(dates)):
            days_diff = (dates[i] - dates[i-1]).days
            intervals.append(days_diff)
        
        if not intervals:
            return None
        
        # Analyze intervals to determine frequency
        frequency_analysis = self._analyze_intervals(intervals)
        
        if not frequency_analysis:
            return None
        
        frequency, interval, confidence = frequency_analysis
        
        # Calculate pattern statistics
        amounts = [abs(t.amount_cents) for t in transactions]
        avg_amount = int(sum(amounts) / len(amounts))
        std_dev = math.sqrt(sum((a - avg_amount) ** 2 for a in amounts) / len(amounts))
        
        # Adjust confidence based on amount consistency
        amount_consistency = max(0, 1.0 - (std_dev / avg_amount)) if avg_amount > 0 else 0
        adjusted_confidence = (confidence * 0.7) + (amount_consistency * 0.3)
        
        # Determine most common category
        categories = [t.category_id for t in transactions if t.category_id]
        most_common_category = Counter(categories).most_common(1)
        category_id = most_common_category[0][0] if most_common_category else None
        
        return RecurringPattern(
            merchant=transactions[0].description,
            normalized_merchant=merchant,
            amount_cents=avg_amount,
            amounts=amounts,
            transaction_ids=[t.id for t in transactions],
            dates=dates,
            frequency=frequency,
            interval=interval,
            confidence_score=adjusted_confidence,
            category_id=category_id,
            account_id=transactions[0].account_id,  # Assume same account for now
            avg_amount_cents=avg_amount,
            std_dev_cents=std_dev,
            detection_method="temporal_analysis"
        )
    
    def _analyze_intervals(self, intervals: List[int]) -> Optional[Tuple[FrequencyType, int, float]]:
        """
        Analyze intervals to determine the most likely frequency pattern.
        
        Returns:
            Tuple of (frequency_type, interval_multiplier, confidence_score) or None
        """
        if not intervals:
            return None
        
        # Calculate basic statistics
        avg_interval = sum(intervals) / len(intervals)
        
        # Check each frequency type
        frequency_scores = []
        
        # Weekly (7 days ± tolerance)
        weekly_score = self._calculate_frequency_score(intervals, 7, FrequencyType.WEEKLY)
        if weekly_score > 0:
            frequency_scores.append((FrequencyType.WEEKLY, 1, weekly_score))
        
        # Bi-weekly (14 days ± tolerance)
        biweekly_score = self._calculate_frequency_score(intervals, 14, FrequencyType.BIWEEKLY)
        if biweekly_score > 0:
            frequency_scores.append((FrequencyType.BIWEEKLY, 1, biweekly_score))
        
        # Monthly (28-31 days, use 30 as target)
        monthly_score = self._calculate_frequency_score(intervals, 30, FrequencyType.MONTHLY)
        if monthly_score > 0:
            frequency_scores.append((FrequencyType.MONTHLY, 1, monthly_score))
        
        # Quarterly (90 days ± tolerance)
        quarterly_score = self._calculate_frequency_score(intervals, 90, FrequencyType.QUARTERLY)
        if quarterly_score > 0:
            frequency_scores.append((FrequencyType.QUARTERLY, 1, quarterly_score))
        
        # Annual (365 days ± tolerance)
        annual_score = self._calculate_frequency_score(intervals, 365, FrequencyType.ANNUALLY)
        if annual_score > 0:
            frequency_scores.append((FrequencyType.ANNUALLY, 1, annual_score))
        
        # Return the best match
        if frequency_scores:
            return max(frequency_scores, key=lambda x: x[2])
        
        return None
    
    def _calculate_frequency_score(self, intervals: List[int], target_days: int, frequency: FrequencyType) -> float:
        """Calculate how well intervals match a target frequency."""
        tolerance = self.FREQUENCY_TOLERANCES.get(frequency, 3)
        
        matching_intervals = 0
        total_deviation = 0
        
        for interval in intervals:
            deviation = abs(interval - target_days)
            if deviation <= tolerance:
                matching_intervals += 1
                total_deviation += deviation
        
        if matching_intervals == 0:
            return 0.0
        
        # Calculate score based on match ratio and average deviation
        match_ratio = matching_intervals / len(intervals)
        avg_deviation = total_deviation / matching_intervals
        deviation_penalty = avg_deviation / tolerance
        
        score = match_ratio * (1.0 - deviation_penalty)
        return max(0.0, min(1.0, score))
    
    def get_suggestions_for_user(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get user-friendly recurring transaction suggestions.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of suggestion dictionaries ready for API response
        """
        patterns = self.detect_patterns_for_user(user_id)
        
        suggestions = []
        for pattern in patterns:
            # Check if we already have a rule for this pattern
            existing_rule = self.db.query(RecurringTransactionRule).filter(
                and_(
                    RecurringTransactionRule.user_id == user_id,
                    RecurringTransactionRule.account_id == pattern.account_id,
                    func.lower(RecurringTransactionRule.description).contains(
                        pattern.normalized_merchant.lower()
                    ),
                    func.abs(RecurringTransactionRule.amount_cents - pattern.amount_cents) <= 
                    (pattern.amount_cents * 0.15)  # 15% tolerance
                )
            ).first()
            
            if existing_rule:
                continue  # Skip if rule already exists
            
            suggestions.append({
                "id": f"pattern_{hash(pattern.normalized_merchant + str(pattern.amount_cents))}",
                "merchant": pattern.merchant,
                "normalized_merchant": pattern.normalized_merchant,
                "amount_cents": pattern.avg_amount_cents,
                "amount_dollars": pattern.avg_amount_cents / 100.0,
                "currency": "USD",  # TODO: Get from transaction
                "frequency": pattern.frequency.value,
                "interval": pattern.interval,
                "confidence_score": round(pattern.confidence_score, 2),
                "category_id": pattern.category_id,
                "account_id": pattern.account_id,
                "sample_dates": [d.isoformat() for d in pattern.dates[-5:]],  # Last 5 dates
                "transaction_count": len(pattern.transaction_ids),
                "amount_variation": {
                    "min_cents": min(pattern.amounts),
                    "max_cents": max(pattern.amounts),
                    "std_dev_cents": round(pattern.std_dev_cents, 2)
                },
                "next_expected_date": self._calculate_next_expected_date(pattern).isoformat(),
                "detection_method": pattern.detection_method
            })
        
        return suggestions
    
    def _calculate_next_expected_date(self, pattern: RecurringPattern) -> date:
        """Calculate when the next transaction is expected based on the pattern."""
        if not pattern.dates:
            return date.today()
        
        last_date = pattern.dates[-1]
        
        if pattern.frequency == FrequencyType.WEEKLY:
            return last_date + timedelta(days=7 * pattern.interval)
        elif pattern.frequency == FrequencyType.BIWEEKLY:
            return last_date + timedelta(days=14 * pattern.interval)
        elif pattern.frequency == FrequencyType.MONTHLY:
            # Approximate monthly calculation
            return last_date + timedelta(days=30 * pattern.interval)
        elif pattern.frequency == FrequencyType.QUARTERLY:
            return last_date + timedelta(days=90 * pattern.interval)
        elif pattern.frequency == FrequencyType.ANNUALLY:
            return last_date + timedelta(days=365 * pattern.interval)
        else:
            # Default to monthly
            return last_date + timedelta(days=30)
    
    def create_rule_from_suggestion(self, user_id: UUID, suggestion: Dict[str, Any]) -> RecurringTransactionRule:
        """
        Create a RecurringTransactionRule from a user-approved suggestion.
        
        Args:
            user_id: UUID of the user
            suggestion: Suggestion dictionary from get_suggestions_for_user
            
        Returns:
            Created RecurringTransactionRule instance
        """
        # Calculate start date and next due date
        start_date = date.today()
        
        # Calculate next due date based on the pattern
        if 'next_expected_date' in suggestion:
            next_due_date = date.fromisoformat(suggestion['next_expected_date'])
        else:
            # Fallback calculation
            next_due_date = start_date + timedelta(days=30)  # Default to 30 days
        
        # Create the rule
        rule = RecurringTransactionRule(
            user_id=user_id,
            account_id=suggestion['account_id'],
            category_id=suggestion.get('category_id'),
            name=f"Recurring: {suggestion['merchant'][:50]}",
            description=suggestion['merchant'],
            amount_cents=suggestion['amount_cents'],
            currency=suggestion.get('currency', 'USD'),
            frequency=FrequencyType(suggestion['frequency']),
            interval=suggestion['interval'],
            start_date=start_date,
            next_due_date=next_due_date,
            tolerance_cents=max(int(suggestion['amount_cents'] * 0.15), 100),  # 15% or $1 minimum
            auto_categorize=True,
            generate_notifications=True,
            is_active=True,
            is_confirmed=True,
            confidence_score=suggestion['confidence_score'],
            detection_method=suggestion.get('detection_method', 'ml_pattern'),
            sample_transactions={
                'transaction_count': suggestion.get('transaction_count', 0),
                'sample_dates': suggestion.get('sample_dates', []),
                'amount_variation': suggestion.get('amount_variation', {})
            }
        )
        
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        return rule