from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import Optional, Dict, Any
from uuid import UUID

from .base import BaseModel


class SavedFilter(BaseModel):
    __tablename__ = "saved_filters"
    
    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Filter details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default={})
    
    # Relationships
    user = relationship("User", back_populates="saved_filters")
    
    def __repr__(self):
        return f"<SavedFilter(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_saved_filters_user_id', 'user_id'),
        Index('idx_saved_filters_name', 'name'),
    )