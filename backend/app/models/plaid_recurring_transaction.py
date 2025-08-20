# Standard library imports
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

# Third-party imports
from sqlalchemy import String, BigInteger, Boolean, Date, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, relationship, mapped_column

# Local imports
from .base import BaseModel

class PlaidRecurringTransaction(BaseModel):
    """Model for Plaid-detected recurring transactions"""
    __tablename__ = "plaid_recurring_transactions"

    # Core identifiers
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    plaid_recurring_transaction_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    plaid_account_id: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Transaction details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Plaid-specific data
    plaid_frequency: Mapped[str] = mapped_column(String(50), nullable=False)  # WEEKLY, MONTHLY, etc.
    plaid_status: Mapped[str] = mapped_column(String(50), nullable=False)  # MATURE, EARLY_DETECTION
    plaid_category: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    last_amount_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # User preferences
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_linked_to_rule: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linked_rule_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        nullable=True
    )
    
    # Sync tracking
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sync_count: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    
    # Raw Plaid data for debugging
    plaid_raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="plaid_recurring_transactions")
    account = relationship("Account", back_populates="plaid_recurring_transactions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_plaid_recurring_user', 'user_id'),
        Index('idx_plaid_recurring_account', 'account_id'),
        Index('idx_plaid_recurring_transaction_id', 'plaid_recurring_transaction_id'),
        Index('idx_plaid_recurring_sync', 'last_sync_at'),
        Index('idx_plaid_recurring_status', 'plaid_status', 'is_muted'),
        Index('idx_plaid_recurring_frequency', 'plaid_frequency'),
        Index('idx_plaid_recurring_linked', 'is_linked_to_rule', 'linked_rule_id'),
    )
    
    @property
    def amount_dollars(self) -> float:
        """Convert cents to dollars for display"""
        return self.amount_cents / 100.0
    
    @property
    def last_amount_dollars(self) -> Optional[float]:
        """Convert last amount cents to dollars for display"""
        return self.last_amount_cents / 100.0 if self.last_amount_cents else None
    
    @property
    def is_mature(self) -> bool:
        """Check if this is a mature recurring transaction pattern"""
        return self.plaid_status == "MATURE"
    
    @property
    def monthly_estimated_amount_cents(self) -> int:
        """Estimate monthly cost based on frequency"""
        if self.plaid_frequency == "WEEKLY":
            return int(self.amount_cents * 52 / 12)  # 52 weeks / 12 months
        elif self.plaid_frequency == "BIWEEKLY":
            return int(self.amount_cents * 26 / 12)  # 26 biweekly periods / 12 months
        elif self.plaid_frequency == "MONTHLY":
            return self.amount_cents
        elif self.plaid_frequency == "QUARTERLY":
            return int(self.amount_cents / 3)  # Quarterly / 3 months
        elif self.plaid_frequency == "ANNUALLY":
            return int(self.amount_cents / 12)  # Annual / 12 months
        else:
            # For unknown frequencies, assume monthly
            return self.amount_cents
    
    def __repr__(self) -> str:
        return (
            f"<PlaidRecurringTransaction("
            f"id={self.id}, "
            f"description='{self.description[:30]}...', "
            f"amount=${self.amount_dollars:.2f}, "
            f"frequency={self.plaid_frequency}, "
            f"status={self.plaid_status})>"
        )