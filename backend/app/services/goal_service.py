from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from ..models.goal import Goal, GoalContribution, GoalMilestone, GoalStatus, GoalType, GoalPriority
from ..schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalContributionCreate,
    MilestoneAlert,
    Goal as GoalSchema,
    GoalContribution as GoalContributionSchema,
    GoalMilestone as GoalMilestoneSchema,
)
from ..websocket.manager import RedisWebSocketManager
from .notification_service import NotificationService
from .base_service import BaseService
import json
from uuid import UUID

class GoalService(BaseService[Goal, GoalCreate, GoalUpdate]):
    """CRUD service for Goal entities with business logic for contributions and milestones."""
    def __init__(self, websocket_manager: RedisWebSocketManager = None):
        super().__init__(Goal)
        self.websocket_manager = websocket_manager

    def create_goal(self, db: Session, user_id: UUID, goal_data: GoalCreate) -> Goal:
        """Create a new financial goal"""
        goal = Goal(
            user_id=user_id,
            **goal_data.model_dump(mode="json")
        )
        
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        # Send real-time update
        if self.websocket_manager:
            # Ensure websocket payload is JSON-serializable
            serialized_goal = GoalSchema.model_validate(goal, from_attributes=True).model_dump(mode="json")
            self._send_goal_update(user_id, "goal_created", serialized_goal)
        
        return goal

    def get_goals(
        self, 
        db: Session, 
        user_id: UUID, 
        status: Optional[GoalStatus] = None,
        goal_type: Optional[GoalType] = None,
        priority: Optional[GoalPriority] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get user's goals with filtering and stats"""
        query = db.query(Goal).filter(Goal.user_id == user_id)
        
        if status:
            query = query.filter(Goal.status == status)
        if goal_type:
            query = query.filter(Goal.goal_type == goal_type)
        if priority:
            query = query.filter(Goal.priority == priority)
        
        # Get total count
        total = query.count()
        
        # Get goals with relationships
        goals = query.options(
            joinedload(Goal.contributions),
            joinedload(Goal.milestones)
        ).offset(skip).limit(limit).all()
        
        # Calculate stats
        all_goals = db.query(Goal).filter(Goal.user_id == user_id).all()
        stats = self._calculate_goal_stats(all_goals)
        
        return {
            "goals": goals,
            "total": total,
            **stats
        }

    # Get a specific goal 
    def get_goal(self, db: Session, user_id: UUID, goal_id: UUID) -> Optional[Goal]:
        """Get a specific goal with all related data"""
        return db.query(Goal).options(
            # joinedload is a SQLAlchemy function for eager-loading relationships in a single database query 
            # (using SQL JOINs instead of running additional queries per relation).
            joinedload(Goal.contributions),
            joinedload(Goal.milestones)
        ).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()

    def update_goal(self, db: Session, user_id: UUID, goal_id: UUID, goal_data: GoalUpdate) -> Optional[Goal]:
        """Update an existing goal"""
        goal = self.get_goal(db, user_id, goal_id)
        if not goal:
            return None
        
        update_data = goal_data.model_dump(exclude_unset=True)
        
        # Handle status changes
        # Completed date depends on status change so we need to handle it separately
        if "status" in update_data:
            if update_data["status"] == GoalStatus.COMPLETED and goal.status != GoalStatus.COMPLETED:
                # Record completion time when transitioning to COMPLETED
                update_data["completed_date"] = datetime.now(timezone.utc)
            elif update_data["status"] != GoalStatus.COMPLETED:
                update_data["completed_date"] = None
        
        # Update goal with new data
        for field, value in update_data.items():
            setattr(goal, field, value)
        
        db.commit()
        db.refresh(goal)
        
        # Send real-time update
        if self.websocket_manager:
            # Ensure websocket payload is JSON-serializable
            serialized_goal = GoalSchema.model_validate(goal, from_attributes=True).model_dump(mode="json")
            self._send_goal_update(user_id, "goal_updated", serialized_goal)
        
        return goal

    def delete_goal(self, db: Session, user_id: UUID, goal_id: UUID) -> bool:
        """Delete a goal and all related data"""
        goal = self.get_goal(db, user_id, goal_id)
        if not goal:
            return False
        
        db.delete(goal)
        db.commit()
        
        # Send real-time update
        if self.websocket_manager:
            self._send_goal_update(user_id, "goal_deleted", {"id": goal_id})
        
        return True

    async def add_contribution(
        self, 
        db: Session, 
        user_id: UUID, 
        goal_id: UUID, 
        contribution_data: GoalContributionCreate,
        transaction_id: Optional[UUID] = None
    ) -> Optional[GoalContribution]:
        """Add a contribution to a goal"""
        goal = db.query(Goal).options(
            joinedload(Goal.contributions),
            joinedload(Goal.milestones)
        ).filter(
            Goal.id == goal_id, 
            Goal.user_id == user_id
        ).with_for_update().first()
        
        if not goal or goal.status not in [GoalStatus.ACTIVE]:
            return None
        
        # Create contribution
        contribution = GoalContribution(
            goal_id=goal_id,
            amount_cents=contribution_data.amount_cents,
            transaction_id=transaction_id
        )
        
        # Update goal progress
        goal.current_amount_cents += contribution_data.amount_cents
        goal.last_contribution_date = datetime.now(timezone.utc)
        
        # Check for milestones
        milestones_reached = await self._check_milestones(db, goal)
        
        # Check if goal is completed
        if goal.current_amount_cents >= goal.target_amount_cents:
            goal.status = GoalStatus.COMPLETED
            goal.completed_date = datetime.now(timezone.utc)
        
        db.add(contribution)
        db.commit()
        db.refresh(contribution)
        db.refresh(goal)
        
        # Send real-time updates
        if self.websocket_manager:
            # Ensure websocket payload is JSON-serializable
            payload = {
                "goal": GoalSchema.model_validate(goal, from_attributes=True).model_dump(mode="json"),
                "contribution": GoalContributionSchema.model_validate(contribution, from_attributes=True).model_dump(mode="json"),
                "milestones": [
                    GoalMilestoneSchema.model_validate(m, from_attributes=True).model_dump(mode="json")
                    for m in milestones_reached
                ],
            }
            self._send_goal_update(user_id, "contribution_added", payload)
            
            # Send milestone alerts
            for milestone in milestones_reached:
                self._send_milestone_alert(user_id, goal, milestone)
            
            # Send completion celebration
            if goal.status == GoalStatus.COMPLETED:
                self._send_goal_completion(user_id, goal)
        
        return contribution

    def get_goal_stats(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive goal statistics"""
        goals = db.query(Goal).filter(Goal.user_id == user_id).all()
        # Reuse existing aggregation then adapt to GoalStats schema shape
        raw_stats = self._calculate_goal_stats(goals)
        contribution_stats = self._get_contribution_stats(db, user_id)

        # Build detailed maps expected by frontend (counts + cent amounts)
        goals_by_type_detail = {}
        for key, value in raw_stats.get("goals_by_type", {}).items():
            normalized_key = str(key).lower()
            goals_by_type_detail[normalized_key] = {
                "count": value.get("count", 0),
                # Provide both plain and _cents keys for compatibility
                "total_amount": value.get("total_amount_cents", 0),
                "current_amount": value.get("current_amount_cents", 0),
                "total_amount_cents": value.get("total_amount_cents", 0),
                "current_amount_cents": value.get("current_amount_cents", 0),
            }

        goals_by_priority_detail = {}
        for key, value in raw_stats.get("goals_by_priority", {}).items():
            normalized_key = str(key).lower()
            goals_by_priority_detail[normalized_key] = {
                "count": value.get("count", 0),
                "total_amount": value.get("total_amount_cents", 0),
                "current_amount": value.get("current_amount_cents", 0),
                "total_amount_cents": value.get("total_amount_cents", 0),
                "current_amount_cents": value.get("current_amount_cents", 0),
            }

        # Normalize contribution stats to *_cents keys the UI expects
        contribution_stats_normalized = {
            "total_contributions_cents": contribution_stats.get("total_contributions", 0),
            "this_month_cents": contribution_stats.get("this_month", 0),
            "last_month_cents": contribution_stats.get("last_month", 0),
            "average_monthly_cents": contribution_stats.get("average_monthly", 0),
            "contribution_trend": [
                {
                    "month": item.get("month"),
                    "amount_cents": int(item.get("amount", 0)),
                    "amount": int(item.get("amount", 0)),
                }
                for item in contribution_stats.get("contribution_trend", [])
            ],
        }

        return {
            "total_goals": raw_stats.get("total_goals", 0),
            "active_goals": raw_stats.get("active_goals", 0),
            "completed_goals": raw_stats.get("completed_goals", 0),
            "paused_goals": raw_stats.get("paused_goals", 0),
            "average_progress": raw_stats.get("average_progress", 0),
            "total_saved_cents": raw_stats.get("total_current_amount_cents", 0),
            "total_target_cents": raw_stats.get("total_target_amount_cents", 0),
            "this_month_contributions_cents": contribution_stats.get("this_month", 0),
            "goals_by_type": goals_by_type_detail,
            "goals_by_priority": goals_by_priority_detail,
            "contribution_stats": contribution_stats_normalized,
        }


    def _calculate_goal_stats(self, goals: List[Goal]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for goals"""
        total_goals = len(goals)
        active_goals = len([g for g in goals if g.status == GoalStatus.ACTIVE])
        completed_goals = len([g for g in goals if g.status == GoalStatus.COMPLETED])
        paused_goals = len([g for g in goals if g.status == GoalStatus.PAUSED])
        
        # Sum in cents to align with API schemas
        total_target = sum(getattr(g, 'target_amount_cents', 0) for g in goals)
        total_current = sum(getattr(g, 'current_amount_cents', 0) for g in goals)
        
        # Progress calculation
        overall_progress = int((total_current / total_target * 100)) if total_target > 0 else 0
        average_progress = int(sum(g.progress_percentage for g in goals) / total_goals) if total_goals > 0 else 0
        
        # Goals by type and priority
        goals_by_type = {}
        goals_by_priority = {}
        
        for goal in goals:
            # By type
            goal_type = goal.goal_type.value
            if goal_type not in goals_by_type:
                goals_by_type[goal_type] = {"count": 0, "total_amount": 0, "current_amount": 0}
            goals_by_type[goal_type]["count"] += 1
            goals_by_type[goal_type]["total_amount_cents"] = goals_by_type[goal_type].get("total_amount_cents", 0) + getattr(goal, 'target_amount_cents', 0)
            goals_by_type[goal_type]["current_amount_cents"] = goals_by_type[goal_type].get("current_amount_cents", 0) + getattr(goal, 'current_amount_cents', 0)
            
            # By priority
            priority = goal.priority.value
            if priority not in goals_by_priority:
                goals_by_priority[priority] = {"count": 0, "total_amount": 0, "current_amount": 0}
            goals_by_priority[priority]["count"] += 1
            goals_by_priority[priority]["total_amount_cents"] = goals_by_priority[priority].get("total_amount_cents", 0) + getattr(goal, 'target_amount_cents', 0)
            goals_by_priority[priority]["current_amount_cents"] = goals_by_priority[priority].get("current_amount_cents", 0) + getattr(goal, 'current_amount_cents', 0)
        
        return {
            "active_goals": active_goals,
            "completed_goals": completed_goals,
            "total_target_amount_cents": total_target,
            "total_current_amount_cents": total_current,
            "overall_progress": overall_progress,
            "total_goals": total_goals,
            "paused_goals": paused_goals,
            "average_progress": average_progress,
            "goals_by_type": goals_by_type,
            "goals_by_priority": goals_by_priority
        }

    def _get_contribution_stats(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get contribution statistics and trends"""
        # Get contributions for user's goals
        contributions = db.query(GoalContribution).join(Goal).filter(
            Goal.user_id == user_id
        ).all()
        
        total_contributions = sum(c.amount_cents for c in contributions)
        
        # This month and last month
        now = datetime.now(timezone.utc)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        this_month = sum(
            c.amount_cents for c in contributions 
            if c.contribution_date >= this_month_start
        )
        
        last_month = sum(
            c.amount_cents for c in contributions 
            if last_month_start <= c.contribution_date < this_month_start
        )
        
        # Monthly trend (last 12 months)
        monthly_data = db.query(
            # Extract year and month from contribution date
            extract('year', GoalContribution.contribution_date).label('year'),
            extract('month', GoalContribution.contribution_date).label('month'),
            func.sum(GoalContribution.amount_cents).label('total')
        ).join(Goal).filter(
            Goal.user_id == user_id,
            GoalContribution.contribution_date >= now - timedelta(days=365)
        ).group_by('year', 'month').all()
        
        contribution_trend = [
            {
                "month": f"{int(row.year)}-{int(row.month):02d}",
                "amount": float(row.total)
            }
            for row in monthly_data
        ]
        
        # Calculate average
        months_with_data = len(contribution_trend)
        average_monthly = int(total_contributions / max(months_with_data, 1))
        
        return {
            "total_contributions": total_contributions,
            "this_month": this_month,
            "last_month": last_month,
            "average_monthly": average_monthly,
            "contribution_trend": contribution_trend
        }

    async def _check_milestones(self, db: Session, goal: Goal) -> List[GoalMilestone]:
        """Check and create milestone records for goal progress"""
        milestones_reached = []
        current_percentage = goal.progress_percentage
        
        # Check for milestone intervals (25%, 50%, 75%, 100%)
        milestone_intervals = [25, 50, 75, 100]
        
        for percentage in milestone_intervals:
            if (current_percentage >= percentage and 
                goal.last_milestone < percentage):
                
                milestone = GoalMilestone(
                    goal_id=goal.id,
                    percentage=percentage,
                    amount_reached_cents=goal.current_amount_cents,
                    celebration_message=self._get_celebration_message(goal.name, percentage)
                )
                
                db.add(milestone)
                milestones_reached.append(milestone)
                goal.last_milestone = percentage
                
                # Create persistent notification for milestone
                try:
                    if percentage == 100:
                        # Goal achieved
                        await NotificationService.create_goal_achieved(
                            db=db,
                            user_id=goal.user_id,
                            goal_name=goal.name,
                            final_amount=goal.current_amount_cents / 100,  # Convert to dollars
                            goal_id=goal.id
                        )
                    else:
                        # Milestone reached
                        await NotificationService.create_goal_milestone(
                            db=db,
                            user_id=goal.user_id,
                            goal_name=goal.name,
                            milestone_percentage=percentage,
                            current_amount=goal.current_amount_cents / 100,  # Convert to dollars
                            target_amount=goal.target_amount_cents / 100,  # Convert to dollars
                            goal_id=goal.id
                        )
                except Exception as e:
                    # Log error but don't fail the milestone creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create goal notification for goal {goal.id}: {e}")
        
        return milestones_reached

    def _get_celebration_message(self, goal_name: str, percentage: float) -> str:
        """Generate celebration messages for milestones"""
        messages = {
            25: f"🎉 Great start! You're 25% of the way to '{goal_name}'!",
            50: f"🚀 Halfway there! You've reached 50% of '{goal_name}'!",
            75: f"💪 Almost there! You're 75% complete with '{goal_name}'!",
            100: f"🎊 Congratulations! You've achieved your goal: '{goal_name}'!"
        }
        return messages.get(percentage, f"Milestone reached: {percentage}% of '{goal_name}'")


    def _send_goal_update(self, user_id: UUID, event_type: str, data: Any):
        """Send real-time goal updates via WebSocket.
        Fire-and-forget scheduling to the async WebSocket manager.
        """
        if self.websocket_manager:
            message = {
                "type": event_type,
                "data": data,
            }
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(self.websocket_manager.send_to_user(str(user_id), message))
            except RuntimeError:
                # No running loop (unlikely in FastAPI request context); ignore gracefully
                pass

    def _send_milestone_alert(self, user_id: UUID, goal: Goal, milestone: GoalMilestone):
        """Send milestone achievement alert"""
        if self.websocket_manager:
            alert = MilestoneAlert(
                goal_id=goal.id,
                goal_name=goal.name,
                milestone_percentage=milestone.percentage,
                amount_reached=milestone.amount_reached,
                celebration_message=milestone.celebration_message,
                reached_date=milestone.reached_date
            )
            
            message = {
                "type": "milestone_reached",
                "data": alert.model_dump(),
            }
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(self.websocket_manager.send_to_user(str(user_id), message))
            except RuntimeError:
                pass

    def _send_goal_completion(self, user_id: UUID, goal: Goal):
        """Send goal completion celebration"""
        if self.websocket_manager:
            message = {
                "type": "goal_completed",
                "data": {
                    "goal_id": goal.id,
                    "goal_name": goal.name,
                    "final_amount": goal.current_amount_cents,
                    "completion_date": goal.completed_date.isoformat() if goal.completed_date else None,
                    "celebration_message": f"🎊 Amazing! You've completed '{goal.name}'! Time to celebrate your achievement!",
                },
            }
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(self.websocket_manager.send_to_user(str(user_id), message))
            except RuntimeError:
                pass


# Provider function with lazy caching
_goal_service_instance = None

def get_goal_service() -> GoalService:
    """Get the global GoalService instance with lazy initialization"""
    global _goal_service_instance
    if _goal_service_instance is None:
        _goal_service_instance = GoalService()
    return _goal_service_instance
