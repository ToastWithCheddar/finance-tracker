from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc
import uuid

from ..models.notification import Notification, NotificationType, NotificationPriority
from ..websocket.events import WebSocketEvents
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    
    @staticmethod
    async def create_notification(
        db: Session,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create a new notification and emit it via WebSocket"""
        try:
            # Create and persist notification
            notification = Notification(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                priority=priority,
                action_url=action_url,
                extra_data=extra_data
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Emit real-time WebSocket notification
            await WebSocketEvents.emit_notification(
                user_id=str(user_id),
                title=title,
                message=message,
                notification_type=type.value,
                priority=priority.value,
                action_url=action_url,
                metadata=extra_data
            )
            
            logger.info(f"Created and emitted notification {notification.id} for user {user_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def get_notifications(
        db: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
        type_filter: Optional[NotificationType] = None
    ) -> List[Notification]:
        """Get notifications for a user with optional filtering"""
        query = db.query(Notification).filter(
            Notification.user_id == user_id
        ).order_by(desc(Notification.created_at))
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
            
        if type_filter:
            query = query.filter(Notification.type == type_filter)
            
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
        """Get count of unread notifications for a user"""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
    
    @staticmethod
    def mark_as_read(
        db: Session, 
        notification_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[Notification]:
        """Mark a notification as read"""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            db.commit()
            db.refresh(notification)
            
        return notification
    
    @staticmethod
    def mark_all_as_read(db: Session, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for a user"""
        updated_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({Notification.is_read: True})
        
        db.commit()
        return updated_count
    
    @staticmethod
    def dismiss_notification(
        db: Session, 
        notification_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> bool:
        """Dismiss (delete) a notification"""
        result = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).delete()
        
        db.commit()
        return result > 0
    
    @staticmethod
    def cleanup_old_notifications(
        db: Session,
        days_to_keep: int = 90
    ) -> int:
        """Clean up old notifications (system maintenance)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = db.query(Notification).filter(
            Notification.created_at < cutoff_date
        ).delete()
        
        db.commit()
        return deleted_count
    
    # Convenience methods for common notification types
    
    @staticmethod
    async def create_budget_alert(
        db: Session,
        user_id: uuid.UUID,
        budget_name: str,
        current_amount_cents: int,
        budget_limit_cents: int,
        percentage_used: float,
        budget_id: uuid.UUID
    ) -> Notification:
        """Create a budget alert notification"""
        # Convert cents to dollars only for display purposes
        current_dollars = current_amount_cents / 100.0
        budget_dollars = budget_limit_cents / 100.0
        
        if percentage_used >= 100:
            title = f"Budget Exceeded: {budget_name}"
            message = f"You've exceeded your {budget_name} budget by ${current_dollars - budget_dollars:.2f}"
            priority = NotificationPriority.HIGH
        elif percentage_used >= 80:
            title = f"Budget Warning: {budget_name}"
            message = f"You've used {percentage_used:.0f}% of your {budget_name} budget"
            priority = NotificationPriority.MEDIUM
        else:
            title = f"Budget Alert: {budget_name}"
            message = f"You've used {percentage_used:.0f}% of your {budget_name} budget"
            priority = NotificationPriority.LOW
            
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.BUDGET_ALERT,
            title=title,
            message=message,
            priority=priority,
            action_url=f"/budgets?budgetId={budget_id}",
            extra_data={
                "budget_id": str(budget_id),
                "percentage_used": percentage_used,
                "current_amount_cents": current_amount_cents,
                "budget_limit_cents": budget_limit_cents
            }
        )
    
    @staticmethod
    async def create_goal_milestone(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        milestone_percentage: float,
        current_amount_cents: int,
        target_amount_cents: int,
        goal_id: uuid.UUID
    ) -> Notification:
        """Create a goal milestone notification"""
        title = f"Goal Milestone: {goal_name}"
        message = f"Congratulations! You've reached {milestone_percentage:.0f}% of your {goal_name} goal"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.GOAL_MILESTONE,
            title=title,
            message=message,
            priority=NotificationPriority.MEDIUM,
            action_url=f"/goals?goalId={goal_id}",
            extra_data={
                "goal_id": str(goal_id),
                "milestone_percentage": milestone_percentage,
                "current_amount_cents": current_amount_cents,
                "target_amount_cents": target_amount_cents
            }
        )
    
    @staticmethod
    async def create_goal_achieved(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        final_amount_cents: int,
        goal_id: uuid.UUID
    ) -> Notification:
        """Create a goal achievement notification"""
        # Convert cents to dollars for display
        final_dollars = final_amount_cents / 100.0
        
        title = f"Goal Achieved: {goal_name}"
        message = f"🎉 Congratulations! You've successfully achieved your {goal_name} goal of ${final_dollars:,.2f}!"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.GOAL_ACHIEVED,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            action_url=f"/goals?goalId={goal_id}",
            extra_data={
                "goal_id": str(goal_id),
                "final_amount_cents": final_amount_cents
            }
        )