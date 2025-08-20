from sqlalchemy import String, BigInteger, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
from app.services.encryption_service import encryption_service

class Account(BaseModel):
    __tablename__ = "accounts"
    
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # checking, savings, credit_card, investment, etc.
    balance_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Plaid Integration Fields
    plaid_account_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    plaid_access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted access token
    plaid_item_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Account metadata and sync status
    account_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Store Plaid metadata, sync status, etc.
    sync_status: Mapped[str] = mapped_column(String(20), default="manual")  # manual, syncing, synced, error, disconnected
    last_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Connection health tracking
    connection_health: Mapped[str] = mapped_column(String(20), default="unknown")  # healthy, warning, failed, not_connected
    sync_frequency: Mapped[str] = mapped_column(String(20), default="manual")  # daily, weekly, monthly, manual
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    plaid_recurring_transactions = relationship("PlaidRecurringTransaction", back_populates="account", cascade="all, delete-orphan")
    
    @property
    def balance_dollars(self) -> float:
        """Convert balance from cents to dollars"""
        return self.balance_cents / 100.0
    
    @property
    def plaid_access_token(self) -> Optional[str]:
        """Get the decrypted Plaid access token"""
        if not self.plaid_access_token_encrypted:
            return None
        return encryption_service.decrypt(self.plaid_access_token_encrypted)
    
    @plaid_access_token.setter
    def plaid_access_token(self, value: Optional[str]) -> None:
        """Set the Plaid access token (will be encrypted)"""
        if value is None:
            self.plaid_access_token_encrypted = None
        else:
            self.plaid_access_token_encrypted = encryption_service.encrypt(value)
    
    @property
    def is_plaid_connected(self) -> bool:
        """Check if account is connected to Plaid"""
        return bool(self.plaid_access_token and self.plaid_account_id)
    
    @property 
    def needs_sync(self) -> bool:
        """Check if account needs synchronization"""
        if not self.is_plaid_connected:
            return False
        
        if not self.last_sync_at:
            return True
            
        # Check if sync is older than 24 hours
        return (datetime.now(timezone.utc) - self.last_sync_at) > timedelta(hours=24)
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', account_type='{self.account_type}', is_active={self.is_active})>"
    
    __table_args__ = (
        Index('idx_account_user_active', 'user_id', 'is_active'),
        Index('idx_account_type_active', 'account_type', 'is_active'),
        Index('idx_account_plaid_id', 'plaid_account_id'),
        Index('idx_account_sync_status', 'sync_status', 'last_sync_at'),
    )