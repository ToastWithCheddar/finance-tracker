from sqlalchemy import String, Boolean, Float, ForeignKey, Index
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from .base import BaseModel
from typing import Optional
from uuid import UUID

class BudgetAlertSettings(BaseModel):
    """Model for configurable budget alert settings"""
    __tablename__ = "budget_alert_settings"
    
    # Relationships
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    budget_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True)
    
    # Alert Configuration
    alert_name: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)  # Alert at 80%
    
    # Notification Channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Alert Behavior
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    repeat_frequency: Mapped[str] = mapped_column(String(20), default="once", nullable=False)  # once, daily, weekly
    
    # Relationships
    user = relationship("User", back_populates="budget_alert_settings")
    budget = relationship("Budget", back_populates="alert_settings")
    
    __table_args__ = (
        Index('idx_budget_alert_user', 'user_id'),
        Index('idx_budget_alert_budget', 'budget_id'),
        Index('idx_budget_alert_active', 'is_active'),
        Index('idx_budget_alert_threshold', 'threshold_percentage'),
    )
    
    def __repr__(self) -> str:
        return f"<BudgetAlertSettings(id={self.id}, name='{self.alert_name}', threshold={self.threshold_percentage})>"