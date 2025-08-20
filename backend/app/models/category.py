from sqlalchemy import String, Boolean, ForeignKey, Index, UniqueConstraint, Integer
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from .base import BaseModel
from typing import Optional
from uuid import UUID

class Category(BaseModel):
    __tablename__ = "categories"
    
    # Basic Information
    user_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Visual
    emoji: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # hex color
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Hierarchy
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # System/Custom
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category", foreign_keys="Transaction.category_id")
    budgets = relationship("Budget", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', is_system={self.is_system}, is_active={self.is_active})>"
    
    __table_args__ = (
        Index('idx_category_user_name', 'user_id', 'name'),
        Index('idx_category_system', 'is_system'),
        Index('idx_category_parent', 'parent_id'),
        UniqueConstraint('user_id', 'name', name='uq_user_category_name'),
    )