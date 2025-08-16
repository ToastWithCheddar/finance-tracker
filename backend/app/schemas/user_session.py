from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserSessionBase(BaseModel):
    device_info: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None


class UserSessionCreate(UserSessionBase):
    session_token: str = Field(..., min_length=1, max_length=255)
    expires_at: Optional[datetime] = None


class UserSessionUpdate(BaseModel):
    device_info: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None
    last_activity: Optional[datetime] = None


class UserSessionResponse(UserSessionBase):
    id: UUID
    user_id: UUID
    is_active: bool
    last_activity: datetime
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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
    current_session_id: Optional[UUID] = None