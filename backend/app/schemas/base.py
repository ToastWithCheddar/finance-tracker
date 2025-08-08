from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )

class TimestampedSchema(BaseSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None

class IdentifiedSchema(BaseSchema):
    id: UUID

class BaseResponseSchema(IdentifiedSchema, TimestampedSchema):
    """Base schema for all entity responses with ID and timestamps"""
    pass