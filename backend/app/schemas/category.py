from pydantic import BaseModel, Field
from typing import List
import uuid
from .base import BaseSchema, TimestampedSchema, IdentifiedSchema
from .validation_types import HexColor

class CategoryBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    emoji: str | None = Field(None, max_length=10)
    color: HexColor = None
    icon: str | None = Field(None, max_length=50)
    sort_order: int = Field(0, ge=0)

class CategoryCreate(CategoryBase):
    parent_id: uuid.UUID | None = None

class CategoryUpdate(BaseSchema):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    emoji: str | None = Field(None, max_length=10)
    color: HexColor = None
    icon: str | None = Field(None, max_length=50)
    parent_id: uuid.UUID | None = None
    sort_order: int | None = Field(None, ge=0)
    is_active: bool | None = None

class CategoryResponse(CategoryBase, IdentifiedSchema, TimestampedSchema):
    user_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    is_system: bool = False
    is_active: bool = True
    children: List["CategoryResponse"] = []
    
    class Config:
        from_attributes = True

# Enable forward references
CategoryResponse.model_rebuild()