from sqlalchemy import String, Boolean, Index
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from typing import Optional
from uuid import UUID, uuid4
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    # Supabase link (for authentication without hashed or locally stored password)
    supabase_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, index=True, default=uuid4)
    
    # Basic Information
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Localization
    locale: Mapped[str] = mapped_column(String(10), default="en-US", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Account Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Preferences
    
    notification_push: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    theme: Mapped[str] = mapped_column(String(20), default="light", nullable=False)
   
    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    plaid_recurring_transactions = relationship("PlaidRecurringTransaction", back_populates="user", cascade="all, delete-orphan")
    categorization_rules = relationship("CategorizationRule", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    
    saved_filters = relationship("SavedFilter", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    budget_alert_settings = relationship("BudgetAlertSettings", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', display_name='{self.display_name}', is_active={self.is_active})>"

    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_supabase_id', 'supabase_user_id'),
    )
