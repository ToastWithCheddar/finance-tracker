from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID

from .base import BaseResponseSchema
from ..models.notification import NotificationType, NotificationPriority


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message")
    type: NotificationType = Field(..., description="Notification type")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Notification priority")
    action_url: Optional[str] = Field(None, max_length=512, description="Optional action URL")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class NotificationCreate(NotificationBase):
    """Schema for creating notifications"""
    pass


class NotificationUpdate(BaseModel):
    """Schema for updating notifications"""
    is_read: Optional[bool] = Field(None, description="Mark as read/unread")


class NotificationResponse(BaseResponseSchema):
    """Schema for notification responses"""
    user_id: UUID = Field(..., description="User ID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    type: NotificationType = Field(..., description="Notification type")
    priority: NotificationPriority = Field(..., description="Notification priority")
    is_read: bool = Field(..., description="Read status")
    action_url: Optional[str] = Field(None, description="Optional action URL")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class NotificationFilter(BaseModel):
    """Schema for filtering notifications"""
    unread_only: bool = Field(False, description="Show only unread notifications")
    type_filter: Optional[NotificationType] = Field(None, description="Filter by notification type")


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list"""
    notifications: List[NotificationResponse] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total number of notifications")
    unread_count: int = Field(..., description="Number of unread notifications")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")


class NotificationStatsResponse(BaseModel):
    """Schema for notification statistics"""
    total_count: int = Field(..., description="Total notifications")
    unread_count: int = Field(..., description="Unread notifications")
    by_type: Dict[str, int] = Field(..., description="Count by notification type")
    by_priority: Dict[str, int] = Field(..., description="Count by priority")


class BulkMarkReadRequest(BaseModel):
    """Schema for bulk mark as read operations"""
    notification_ids: Optional[List[UUID]] = Field(None, description="Specific notification IDs (None for all)")


class BulkMarkReadResponse(BaseModel):
    """Schema for bulk mark as read response"""
    updated_count: int = Field(..., description="Number of notifications marked as read")
    success: bool = Field(..., description="Operation success status")