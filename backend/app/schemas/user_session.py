from pydantic import BaseModel, Field, ConfigDict
# No imports needed from typing for this file after modernization
from datetime import datetime
from uuid import UUID

from .base import BaseResponseSchema


class UserSessionBase(BaseModel):
    device_info: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    location: str | None = None


class UserSessionCreate(UserSessionBase):
    session_token: str = Field(..., min_length=1, max_length=255)
    expires_at: datetime | None = None


class UserSessionUpdate(BaseModel):
    device_info: str | None = None
    location: str | None = None
    is_active: bool | None = None
    last_activity: datetime | None = None


class UserSessionResponse(UserSessionBase, BaseResponseSchema):
    user_id: UUID
    is_active: bool
    last_activity: datetime
    expires_at: datetime | None = None


class UserSessionPublic(BaseModel):
    """Public session info for users to view their own sessions"""
    id: UUID
    device_info: Optional[str] = "Unknown Device"
    location: Optional[str] = "Unknown Location"
    is_active: bool
    last_activity: datetime
    created_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class SessionStatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    inactive_sessions: int
    current_session_id: UUID | None = None