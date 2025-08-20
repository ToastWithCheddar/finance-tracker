from sqlalchemy import String, Text, Boolean, ForeignKey, Index, Enum as SAEnum
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
import enum

class NotificationType(enum.Enum):
    BUDGET_ALERT = "budget_alert"
    GOAL_MILESTONE = "goal_milestone" 
    GOAL_ACHIEVED = "goal_achieved"
    TRANSACTION_ALERT = "transaction_alert"
    LOW_BALANCE_WARNING = "low_balance_warning"
    SYSTEM_ALERT = "system_alert"
    INFO = "info"

class NotificationPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Notification(BaseModel):
    __tablename__ = "notifications"
    
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(SAEnum(NotificationPriority), default=NotificationPriority.MEDIUM)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        title_truncated = self.title[:30] + "..." if len(self.title) > 30 else self.title
        return f"<Notification(id={self.id}, type={self.type.value}, title='{title_truncated}', is_read={self.is_read})>"
    
    __table_args__ = (
        Index('idx_notification_user_read', 'user_id', 'is_read'),
        Index('idx_notification_user_type', 'user_id', 'type'),
        Index('idx_notification_priority', 'priority'),
        Index('idx_notification_created', 'created_at'),
    )