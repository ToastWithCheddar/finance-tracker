from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
import uuid

from ..models.notification import Notification, NotificationType
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
        
        
        return {
            "total_count": total_count,
            "unread_count": unread_count,
            "by_type": by_type
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
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
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
        elif percentage_used >= 80:
            title = f"Budget Warning: {budget_name}"
            message = f"You've used {percentage_used:.0f}% of your {budget_name} budget"
        else:
            title = f"Budget Alert: {budget_name}"
            message = f"You've used {percentage_used:.0f}% of your {budget_name} budget"
            
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.BUDGET_ALERT,
            title=title,
            message=message,
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
            action_url=f"/goals?goalId={goal_id}",
            metadata={
                "goal_id": str(goal_id),
                "final_amount_cents": final_amount_cents
            }
        )
    
    @staticmethod
    async def create_goal_created_notification(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        target_amount_cents: int,
        target_date: datetime,
        goal_id: uuid.UUID
    ) -> Notification:
        """Create a goal created notification"""
        target_dollars = target_amount_cents / 100.0
        target_date_str = target_date.strftime("%B %d, %Y") if target_date else "No deadline"
        
        title = f"New Goal Created: {goal_name}"
        message = f"You've created a new goal to save ${target_dollars:,.2f} by {target_date_str}"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.GOAL_CREATED,
            title=title,
            message=message,
            action_url=f"/goals?goalId={goal_id}",
            metadata={
                "goal_id": str(goal_id),
                "target_amount_cents": target_amount_cents,
                "target_date": target_date.isoformat() if target_date else None
            }
        )
    
    @staticmethod
    async def create_goal_updated_notification(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        changes: Dict[str, Any],
        goal_id: uuid.UUID
    ) -> Notification:
        """Create a goal updated notification"""
        title = f"Goal Updated: {goal_name}"
        
        # Create a summary of changes
        change_descriptions = []
        if "name" in changes:
            change_descriptions.append(f"name changed from '{changes['name']['old']}' to '{changes['name']['new']}'")
        if "target_amount_cents" in changes:
            old_amount = changes["target_amount_cents"]["old"] / 100.0
            new_amount = changes["target_amount_cents"]["new"] / 100.0
            change_descriptions.append(f"target amount updated from ${old_amount:,.2f} to ${new_amount:,.2f}")
        if "target_date" in changes:
            old_date = changes["target_date"]["old"].strftime("%B %d, %Y") if changes["target_date"]["old"] else "No deadline"
            new_date = changes["target_date"]["new"].strftime("%B %d, %Y") if changes["target_date"]["new"] else "No deadline"
            change_descriptions.append(f"target date changed from {old_date} to {new_date}")
        if "description" in changes:
            change_descriptions.append("description updated")
        
        message = f"Your goal has been updated: {'; '.join(change_descriptions)}" if change_descriptions else "Your goal has been updated"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.GOAL_UPDATED,
            title=title,
            message=message,
            action_url=f"/goals?goalId={goal_id}",
            metadata={
                "goal_id": str(goal_id),
                "changes": changes
            }
        )
    
    @staticmethod
    async def create_goal_deleted_notification(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        current_progress_cents: int,
        target_amount_cents: int
    ) -> Notification:
        """Create a goal deleted notification"""
        current_dollars = current_progress_cents / 100.0
        target_dollars = target_amount_cents / 100.0
        completion_percentage = (current_progress_cents / target_amount_cents * 100) if target_amount_cents > 0 else 0
        
        title = f"Goal Deleted: {goal_name}"
        message = f"You've deleted your '{goal_name}' goal. You had saved ${current_dollars:,.2f} of ${target_dollars:,.2f} ({completion_percentage:.1f}% complete)"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.GOAL_DELETED,
            title=title,
            message=message,
            action_url="/goals",
            metadata={
                "goal_name": goal_name,
                "current_progress_cents": current_progress_cents,
                "target_amount_cents": target_amount_cents,
                "completion_percentage": completion_percentage
            }
        )
    
    @staticmethod
    async def create_goal_status_changed_notification(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        old_status: str,
        new_status: str,
        goal_id: uuid.UUID
    ) -> Notification:
        """Create a goal status changed notification"""
        title = f"Goal Status Changed: {goal_name}"
        
        status_messages = {
            "active": "activated and ready for contributions",
            "paused": "paused - contributions are temporarily stopped",
            "completed": "marked as completed",
            "cancelled": "cancelled"
        }
        
        action_description = status_messages.get(new_status, f"changed to {new_status}")
        message = f"Your goal has been {action_description}"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.GOAL_STATUS_CHANGED,
            title=title,
            message=message,
            action_url=f"/goals?goalId={goal_id}",
            metadata={
                "goal_id": str(goal_id),
                "old_status": old_status,
                "new_status": new_status
            }
        )
    
    @staticmethod
    async def create_contribution_added_notification(
        db: Session,
        user_id: uuid.UUID,
        goal_name: str,
        contribution_amount_cents: int,
        new_total_cents: int,
        target_amount_cents: int,
        goal_id: uuid.UUID
    ) -> Notification:
        """Create a contribution added notification"""
        contribution_dollars = contribution_amount_cents / 100.0
        new_total_dollars = new_total_cents / 100.0
        completion_percentage = (new_total_cents / target_amount_cents * 100) if target_amount_cents > 0 else 0
        
        title = f"Contribution Added: {goal_name}"
        message = f"You've added ${contribution_dollars:,.2f} to your goal. New total: ${new_total_dollars:,.2f} ({completion_percentage:.1f}% complete)"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            type=NotificationType.CONTRIBUTION_ADDED,
            title=title,
            message=message,
            action_url=f"/goals?goalId={goal_id}",
            metadata={
                "goal_id": str(goal_id),
                "contribution_amount_cents": contribution_amount_cents,
                "new_total_cents": new_total_cents,
                "target_amount_cents": target_amount_cents,
                "completion_percentage": completion_percentage
            }
        )
