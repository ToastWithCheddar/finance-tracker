from sqlalchemy import String, BigInteger, Boolean, Date, ForeignKey, Float, Index, Enum
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from .base import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID
import enum

class BudgetPeriod(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class Budget(BaseModel):
    __tablename__ = "budgets"
    
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod), default=BudgetPeriod.MONTHLY, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    alert_threshold: Mapped[float] = mapped_column(Float, default=0.8)  # alert at 80%
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")
    alert_settings = relationship("BudgetAlertSettings", back_populates="budget", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Budget(id={self.id}, name='{self.name}', amount_cents={self.amount_cents}, period={self.period.value}, is_active={self.is_active})>"
    
    __table_args__ = (
        Index('idx_budget_user_period', 'user_id', 'period'),
        Index('idx_budget_user_active', 'user_id', 'is_active'),
        Index('idx_budget_date_range', 'start_date', 'end_date'),
        Index('idx_budget_category_active', 'category_id', 'is_active'),
    )