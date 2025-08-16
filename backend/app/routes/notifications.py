from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

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
        
        # Get total count for pagination
        total_count = len(NotificationService.get_notifications(
            db=db,
            user_id=current_user.id,
            skip=0,
            limit=10000,  # Large number to get all
            type_filter=type_filter
        ))
        
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")


@router.get("/stats", response_model=NotificationStatsResponse)
def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification statistics for the current user"""
    try:
        all_notifications = NotificationService.get_notifications(
            db=db,
            user_id=current_user.id,
            skip=0,
            limit=10000  # Large number to get all
        )
        
        unread_count = NotificationService.get_unread_count(
            db=db,
            user_id=current_user.id
        )
        
        # Count by type
        by_type = {}
        by_priority = {}
        
        for notification in all_notifications:
            # Count by type
            type_key = notification.type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # Count by priority
            priority_key = notification.priority.value
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
        
        return NotificationStatsResponse(
            total_count=len(all_notifications),
            unread_count=unread_count,
            by_type=by_type,
            by_priority=by_priority
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notification stats: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return NotificationResponse.model_validate(notification)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update notification: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"success": True, "message": "Notification dismissed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss notification: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"Failed to mark notifications as read: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return NotificationResponse.model_validate(notification)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notification: {str(e)}")