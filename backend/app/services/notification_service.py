from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
import uuid

from ..models.notification import Notification, NotificationType, NotificationPriority
from ..models.user import User
from ..config import settings
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
        metadata: Optional[Dict[str, Any]] = None
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
                metadata=metadata
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
                metadata=metadata
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
    def get_notifications_count(
        db: Session,
        user_id: uuid.UUID,
        unread_only: bool = False,
        type_filter: Optional[NotificationType] = None
    ) -> int:
        """Get total count of notifications for a user with optional filtering"""
        query = db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
            
        if type_filter:
            query = query.filter(Notification.type == type_filter)
            
        return query.scalar() or 0
    
    @staticmethod
    def get_notification_stats_efficient(db: Session, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get notification statistics using efficient SQL aggregation"""
        # Get total count
        total_count = db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id
        ).scalar() or 0
        
        # Get unread count
        unread_count = db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).scalar() or 0
        
        # Get count by type using SQL aggregation
        type_stats = db.query(
            Notification.type,
            func.count(Notification.id).label('count')
        ).filter(
            Notification.user_id == user_id
        ).group_by(Notification.type).all()
        
        by_type = {stat.type.value: stat.count for stat in type_stats}
        
        # Get count by priority using SQL aggregation
        priority_stats = db.query(
            Notification.priority,
            func.count(Notification.id).label('count')
        ).filter(
            Notification.user_id == user_id
        ).group_by(Notification.priority).all()
        
        by_priority = {stat.priority.value: stat.count for stat in priority_stats}
        
        return {
            "total_count": total_count,
            "unread_count": unread_count,
            "by_type": by_type,
            "by_priority": by_priority
        }
    
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
            metadata={
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
            metadata={
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
            metadata={
                "goal_id": str(goal_id),
                "final_amount_cents": final_amount_cents
            }
        )
