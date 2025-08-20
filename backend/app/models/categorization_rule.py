# Standard library imports
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

# Third-party imports
from sqlalchemy import String, BigInteger, Boolean, ForeignKey, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, relationship, mapped_column

# Local imports
from .base import BaseModel

class CategorizationRule(BaseModel):
    """Model for automated transaction categorization rules"""
    __tablename__ = "categorization_rules"
    
    # Basic info
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Rule configuration
    priority: Mapped[int] = mapped_column(BigInteger, default=100, nullable=False)  # Lower = higher priority
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Matching conditions (JSON structure for flexibility)
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Example conditions structure:
    # {
    #   "merchant_contains": ["starbucks", "sbux"],
    #   "description_contains": ["coffee"],
    #   "amount_range": {"min_cents": 100, "max_cents": 2000},
    #   "account_types": ["checking", "credit_card"],
    #   "transaction_type": "expense",
    #   "account_ids": ["uuid1", "uuid2"],
    #   "category_not_in": ["uuid3", "uuid4"]
    # }
    
    # Actions to perform when rule matches
    actions: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Example actions structure:
    # {
    #   "set_category_id": "uuid-of-category",
    #   "add_tags": ["coffee", "daily"],
    #   "set_confidence": 0.95,
    #   "add_note": "Auto-categorized by coffee rule"
    # }
    
    # Rule performance tracking
    times_applied: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    success_rate: Mapped[Optional[float]] = mapped_column(nullable=True)  # User feedback based
    
    # Template info (if created from template)
    template_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    template_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="categorization_rules")
    
    __table_args__ = (
        Index('idx_categorization_rule_user', 'user_id'),
        Index('idx_categorization_rule_priority', 'priority', 'is_active'),
        Index('idx_categorization_rule_performance', 'times_applied', 'success_rate'),
        Index('idx_categorization_rule_template', 'template_id'),
        Index('idx_categorization_rule_active', 'is_active', 'user_id'),
    )
    
    @property
    def success_rate_percentage(self) -> Optional[float]:
        """Get success rate as percentage"""
        return self.success_rate * 100 if self.success_rate is not None else None
    
    @property
    def is_from_template(self) -> bool:
        """Check if rule was created from a template"""
        return self.template_id is not None
    
    def matches_merchant(self, merchant: Optional[str], description: str) -> bool:
        """Check if merchant or description matches merchant conditions"""
        merchant_patterns = self.conditions.get("merchant_contains", [])
        if not merchant_patterns:
            return True
        
        search_text = f"{merchant or ''} {description}".lower()
        return any(pattern.lower() in search_text for pattern in merchant_patterns)
    
    def matches_description(self, description: str) -> bool:
        """Check if description matches description conditions"""
        description_patterns = self.conditions.get("description_contains", [])
        if not description_patterns:
            return True
        
        search_text = description.lower()
        return any(pattern.lower() in search_text for pattern in description_patterns)
    
    def matches_amount(self, amount_cents: int) -> bool:
        """Check if amount matches amount range conditions"""
        amount_range = self.conditions.get("amount_range")
        if not amount_range:
            return True
        
        min_cents = amount_range.get("min_cents")
        max_cents = amount_range.get("max_cents")
        
        if min_cents is not None and amount_cents < min_cents:
            return False
        if max_cents is not None and amount_cents > max_cents:
            return False
        
        return True
    
    def matches_account_type(self, account_type: str) -> bool:
        """Check if account type matches account type conditions"""
        account_types = self.conditions.get("account_types", [])
        if not account_types:
            return True
        
        return account_type in account_types
    
    def matches_transaction_type(self, transaction_type: str) -> bool:
        """Check if transaction type matches conditions"""
        required_type = self.conditions.get("transaction_type")
        if not required_type:
            return True
        
        return transaction_type == required_type
    
    def matches_account_id(self, account_id: UUID) -> bool:
        """Check if account ID matches account ID conditions"""
        account_ids = self.conditions.get("account_ids", [])
        if not account_ids:
            return True
        
        return str(account_id) in account_ids
    
    def exclude_category(self, current_category_id: Optional[UUID]) -> bool:
        """Check if current category should be excluded from rule application"""
        excluded_categories = self.conditions.get("category_not_in", [])
        if not excluded_categories or current_category_id is None:
            return False
        
        return str(current_category_id) in excluded_categories
    
    def get_target_category_id(self) -> Optional[UUID]:
        """Get the category ID to set from actions"""
        category_id = self.actions.get("set_category_id")
        if category_id:
            try:
                return UUID(category_id)
            except (ValueError, TypeError):
                return None
        return None
    
    def get_confidence_score(self) -> Optional[float]:
        """Get confidence score from actions"""
        return self.actions.get("set_confidence")
    
    def get_tags_to_add(self) -> list:
        """Get tags to add from actions"""
        return self.actions.get("add_tags", [])
    
    def get_note_to_add(self) -> Optional[str]:
        """Get note to add from actions"""
        return self.actions.get("add_note")
    
    def increment_application_count(self):
        """Increment the times_applied counter and update last_applied_at"""
        self.times_applied += 1
        self.last_applied_at = datetime.utcnow()
    
    def update_success_rate(self, new_feedback: bool):
        """Update success rate based on user feedback"""
        if self.success_rate is None:
            # First feedback
            self.success_rate = 1.0 if new_feedback else 0.0
        else:
            # Weighted average with more weight on recent feedback
            weight = 0.3  # 30% weight for new feedback
            if new_feedback:
                self.success_rate = (1 - weight) * self.success_rate + weight * 1.0
            else:
                self.success_rate = (1 - weight) * self.success_rate + weight * 0.0
    
    def __repr__(self) -> str:
        return (
            f"<CategorizationRule("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"priority={self.priority}, "
            f"active={self.is_active}, "
            f"applied={self.times_applied} times)>"
        )