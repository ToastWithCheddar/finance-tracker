from pydantic import BaseModel, Field, field_validator 
from typing import Optional, List
import uuid
from .base import BaseSchema, TimestampedSchema, IdentifiedSchema

class CategoryBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    emoji: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = Field(0, ge=0)
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            return f"#{v}"
        return v

class CategoryCreate(CategoryBase):
    parent_id: Optional[uuid.UUID] = None

class CategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    emoji: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[uuid.UUID] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            return f"#{v}"
        return v

class CategoryResponse(CategoryBase, IdentifiedSchema, TimestampedSchema):
    user_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    is_system: bool = False
    is_active: bool = True
    children: List["CategoryResponse"] = []
    
    class Config:
        from_attributes = True

# Enable forward references
CategoryResponse.model_rebuild()