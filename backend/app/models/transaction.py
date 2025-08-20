# Standard library imports
from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID

# Third-party imports
from sqlalchemy import String, BigInteger, Boolean, Date, Text, ForeignKey, Float, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, relationship, mapped_column

# Local imports
from .base import BaseModel

class Transaction(BaseModel):
    __tablename__ = "transactions"

    # Basic Information
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # Transaction Details
    # Why amount_cents: Avoids floating-point precision errors (never store money as decimals!)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False) #  Store money in cents/smallest currency unit
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    merchant: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    merchant_logo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    authorized_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    posted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="posted", nullable=False)  # pending, posted, cancelled
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Identifies subscription/recurring payments
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Distinguishes purchases and account transfers
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Allows users to hide transactions from normal views while preserving them in the database for audit trails
    
    # Recurring Information
    # !!! Pattern: The parent transaction defines the rule, child transactions are generated instances.
    recurring_rule: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # cron-like rules (for subscription etc.)
    recurring_parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    
    # Location (for efficient querying)
    location: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # {lat, lng, address, city, state, country}
    
    # Additional Data
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, default=[])
    
    # External Integration
    plaid_transaction_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    plaid_category: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # ML/AI
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # ML categorization confidence
    ml_suggested_category_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # Metadata
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    
    # Relationships - Use proper imports and foreign keys
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions", foreign_keys=[category_id])
    ml_suggested_category = relationship("Category", foreign_keys=[ml_suggested_category_id])
    recurring_parent = relationship("Transaction", remote_side="Transaction.id", backref="recurring_children")
    goal_contributions = relationship("GoalContribution", back_populates="transaction", cascade="all, delete-orphan")
    
    def __repr__(self):
        merchant_or_desc = self.merchant or self.description[:30] + "..." if len(self.description) > 30 else self.description
        return f"<Transaction(id={self.id}, amount_cents={self.amount_cents}, merchant='{merchant_or_desc}', date={self.transaction_date})>"
    
    __table_args__ = (
        Index('idx_transaction_user_date', 'user_id', 'transaction_date'),
        Index('idx_transaction_account_date', 'account_id', 'transaction_date'),
        Index('idx_transaction_category', 'category_id'),
        Index('idx_transaction_merchant', 'merchant'),
        Index('idx_transaction_amount', 'amount_cents'),
        Index('idx_transaction_status', 'status'),
        Index('idx_transaction_plaid_id', 'plaid_transaction_id'),
        Index('idx_transaction_recurring', 'is_recurring'),
    )