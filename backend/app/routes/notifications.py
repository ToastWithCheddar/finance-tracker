from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from ..database import get_db
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..models.notification import Notification, NotificationType
from ..services.notification_service import NotificationService
from ..schemas.notification import (
    NotificationResponse, NotificationListResponse, NotificationStatsResponse,
    NotificationFilter, BulkMarkReadRequest, BulkMarkReadResponse,
    NotificationUpdate
)
from ..core.exceptions import (
    DataIntegrityError,
    ResourceNotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    type_filter: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user with optional filtering"""
    try:
        notifications = NotificationService.get_notifications(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            unread_only=unread_only,
            type_filter=type_filter
        )
        
        # Get total count for pagination using efficient count query
        total_count = NotificationService.get_notifications_count(
            db=db,
            user_id=current_user.id,
            unread_only=unread_only,
            type_filter=type_filter
        )
        
        unread_count = NotificationService.get_unread_count(
            db=db,
            user_id=current_user.id
        )
        
        return NotificationListResponse(
            notifications=[NotificationResponse.model_validate(notification) for notification in notifications],
            total=total_count,
            unread_count=unread_count,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch notifications for user {current_user.id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve notifications")


@router.get("/stats", response_model=NotificationStatsResponse)
def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification statistics for the current user"""
    try:
        # Use efficient SQL aggregation instead of loading all notifications
        stats = NotificationService.get_notification_stats_efficient(
            db=db,
            user_id=current_user.id
        )
        
        return NotificationStatsResponse(
            total_count=stats["total_count"],
            unread_count=stats["unread_count"],
            by_type=stats["by_type"],
            by_priority=stats["by_priority"]
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch notification stats for user {current_user.id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve notification statistics")


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: uuid.UUID,
    notification_update: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a notification (typically to mark as read)"""
    try:
        if notification_update.is_read is not None:
            if notification_update.is_read:
                notification = NotificationService.mark_as_read(
                    db=db,
                    notification_id=notification_id,
                    user_id=current_user.id
                )
            else:
                # For marking as unread, we need to fetch and update manually
                notification = db.query(Notification).filter(
                    Notification.id == notification_id,
                    Notification.user_id == current_user.id
                ).first()
                
                if notification:
                    notification.is_read = False
                    db.commit()
                    db.refresh(notification)
        
        if not notification:
            raise ResourceNotFoundError("Notification", str(notification_id))
        
        return NotificationResponse.model_validate(notification)
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to update notification {notification_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to update notification")


@router.delete("/{notification_id}")
def dismiss_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dismiss (delete) a notification"""
    try:
        success = NotificationService.dismiss_notification(
            db=db,
            notification_id=notification_id,
            user_id=current_user.id
        )
        
        if not success:
            raise ResourceNotFoundError("Notification", str(notification_id))
        
        return {"success": True, "message": "Notification dismissed successfully"}
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to dismiss notification {notification_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to dismiss notification")


@router.post("/mark-all-read", response_model=BulkMarkReadResponse)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user"""
    try:
        updated_count = NotificationService.mark_all_as_read(
            db=db,
            user_id=current_user.id
        )
        
        return BulkMarkReadResponse(
            updated_count=updated_count,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Failed to mark notifications as read for user {current_user.id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to mark notifications as read")


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific notification by ID"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise ResourceNotFoundError("Notification", str(notification_id))
        
        return NotificationResponse.model_validate(notification)
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch notification {notification_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve notification")