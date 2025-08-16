from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class SavedFilterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the saved filter")
    filters: Dict[str, Any] = Field(..., description="Filter configuration as JSON object")


class SavedFilterCreate(SavedFilterBase):
    pass


class SavedFilterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the saved filter")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter configuration as JSON object")


class SavedFilterResponse(SavedFilterBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True