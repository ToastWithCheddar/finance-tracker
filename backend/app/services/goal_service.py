from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..models.goal import Goal, GoalContribution, GoalMilestone, GoalStatus, GoalType, GoalPriority
from ..schemas.goal import GoalCreate, GoalUpdate, GoalContributionCreate, MilestoneAlert
from ..websocket.manager import WebSocketManager
import json
from uuid import UUID

class GoalService:
    def __init__(self, websocket_manager: WebSocketManager = None):
        self.websocket_manager = websocket_manager

    def create_goal(self, db: Session, user_id: UUID, goal_data: GoalCreate) -> Goal:
        """Create a new financial goal"""
        goal = Goal(
            user_id=user_id,
            **goal_data.model_dump()
        )
        
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        # Send real-time update
        if self.websocket_manager:
            self._send_goal_update(user_id, "goal_created", goal)
        
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
                update_data["completed_date"] = datetime.tcnow()
            elif update_data["status"] != GoalStatus.COMPLETED:
                update_data["completed_date"] = None
        
        # Update goal with new data
        for field, value in update_data.items():
            setattr(goal, field, value)
        
        db.commit()
        db.refresh(goal)
        
        # Send real-time update
        if self.websocket_manager:
            self._send_goal_update(user_id, "goal_updated", goal)
        
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

    def add_contribution(
        self, 
        db: Session, 
        user_id: UUID, 
        goal_id: UUID, 
        contribution_data: GoalContributionCreate,
        transaction_id: Optional[UUID] = None,
        is_automatic: bool = False
    ) -> Optional[GoalContribution]:
        """Add a contribution to a goal"""
        goal = self.get_goal(db, user_id, goal_id)
        if not goal or goal.status not in [GoalStatus.ACTIVE]:
            return None
        
        # Create contribution
        contribution = GoalContribution(
            goal_id=goal_id,
            amount=contribution_data.amount,
            note=contribution_data.note,
            transaction_id=transaction_id,
            is_automatic=is_automatic
        )
        
        # Update goal progress
        goal.current_amount += contribution_data.amount
        goal.last_contribution_date = datetime.now(datetime.timezone.utc)
        
        # Check for milestones
        milestones_reached = self._check_milestones(db, goal)
        
        # Check if goal is completed
        if goal.current_amount >= goal.target_amount:
            goal.status = GoalStatus.COMPLETED
            goal.completed_date = datetime.now(datetime.timezone.utc)
        
        db.add(contribution)
        db.commit()
        db.refresh(contribution)
        db.refresh(goal)
        
        # Send real-time updates
        if self.websocket_manager:
            self._send_goal_update(user_id, "contribution_added", {
                "goal": goal,
                "contribution": contribution,
                "milestones": milestones_reached
            })
            
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
        
        stats = self._calculate_goal_stats(goals)
        
        # Add contribution trends
        contribution_stats = self._get_contribution_stats(db, user_id)
        stats["contribution_stats"] = contribution_stats
        
        return stats

    def process_automatic_contributions(self, db: Session) -> Dict[str, int]:
        """Process automatic contributions for all eligible goals"""
        today = datetime.now(datetime.timezone.utc).date()
        processed = {"success": 0, "failed": 0}
        
        # Get goals with automatic contributions enabled
        auto_goals = db.query(Goal).filter(
            and_(
                Goal.auto_contribute == True,
                Goal.status == GoalStatus.ACTIVE,
                Goal.auto_contribution_amount > 0
            )
        ).all()
        
        for goal in auto_goals:
            try:
                # Check if contribution is due based on frequency
                if self._is_contribution_due(goal, today):
                    contribution_data = GoalContributionCreate(
                        amount=goal.auto_contribution_amount,
                        note=f"Automatic contribution - {goal.contribution_frequency}"
                    )
                    
                    self.add_contribution(
                        db, goal.user_id, goal.id, contribution_data, is_automatic=True
                    )
                    processed["success"] += 1
            except Exception as e:
                print(f"Failed to process automatic contribution for goal {goal.id}: {e}")
                processed["failed"] += 1
        
        return processed

    def _calculate_goal_stats(self, goals: List[Goal]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for goals"""
        total_goals = len(goals)
        active_goals = len([g for g in goals if g.status == GoalStatus.ACTIVE])
        completed_goals = len([g for g in goals if g.status == GoalStatus.COMPLETED])
        paused_goals = len([g for g in goals if g.status == GoalStatus.PAUSED])
        
        total_target = sum(g.target_amount for g in goals)
        total_current = sum(g.current_amount for g in goals)
        
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
            goals_by_type[goal_type]["total_amount"] += goal.target_amount
            goals_by_type[goal_type]["current_amount"] += goal.current_amount
            
            # By priority
            priority = goal.priority.value
            if priority not in goals_by_priority:
                goals_by_priority[priority] = {"count": 0, "total_amount": 0, "current_amount": 0}
            goals_by_priority[priority]["count"] += 1
            goals_by_priority[priority]["total_amount"] += goal.target_amount
            goals_by_priority[priority]["current_amount"] += goal.current_amount
        
        return {
            "active_goals": active_goals,
            "completed_goals": completed_goals,
            "total_target_amount": total_target,
            "total_current_amount": total_current,
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
        
        total_contributions = sum(c.amount for c in contributions)
        
        # This month and last month
        now = datetime.now(datetime.timezone.utc)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        this_month = sum(
            c.amount for c in contributions 
            if c.contribution_date >= this_month_start
        )
        
        last_month = sum(
            c.amount for c in contributions 
            if last_month_start <= c.contribution_date < this_month_start
        )
        
        # Monthly trend (last 12 months)
        monthly_data = db.query(
            # Extract year and month from contribution date
            extract('year', GoalContribution.contribution_date).label('year'),
            extract('month', GoalContribution.contribution_date).label('month'),
            func.sum(GoalContribution.amount).label('total')
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

    def _check_milestones(self, db: Session, goal: Goal) -> List[GoalMilestone]:
        """Check and create milestone records for goal progress"""
        milestones_reached = []
        current_percentage = goal.progress_percentage
        
        # Check for milestone intervals (25%, 50%, 75%, 100%)
        milestone_intervals = [25, 50, 75, 100]
        
        for percentage in milestone_intervals:
            if (current_percentage >= percentage and 
                goal.last_milestone_reached < percentage):
                
                milestone = GoalMilestone(
                    goal_id=goal.id,
                    percentage=percentage,
                    amount_reached=goal.current_amount,
                    celebration_message=self._get_celebration_message(goal.name, percentage)
                )
                
                db.add(milestone)
                milestones_reached.append(milestone)
                goal.last_milestone_reached = percentage
        
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

    def _is_contribution_due(self, goal: Goal, today: datetime.date) -> bool:
        """Check if automatic contribution is due based on frequency"""
        if not goal.last_contribution_date:
            return True
        
        last_contribution = goal.last_contribution_date.date()
        days_since = (today - last_contribution).days
        
        frequency_days = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30  # Approximate
        }
        
        required_days = frequency_days.get(goal.contribution_frequency, 30)
        return days_since >= required_days

    def _send_goal_update(self, user_id: UUID, event_type: str, data: Any):
        """Send real-time goal updates via WebSocket"""
        if self.websocket_manager:
            message = {
                "type": event_type,
                "data": data
            }
            self.websocket_manager.send_to_user(user_id, json.dumps(message))

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
                "data": alert.model_dump()
            }
            self.websocket_manager.send_to_user(user_id, json.dumps(message))

    def _send_goal_completion(self, user_id: UUID, goal: Goal):
        """Send goal completion celebration"""
        if self.websocket_manager:
            message = {
                "type": "goal_completed",
                "data": {
                    "goal_id": goal.id,
                    "goal_name": goal.name,
                    "final_amount": goal.current_amount,
                    "completion_date": goal.completed_date.isoformat(),
                    "celebration_message": f"🎊 Amazing! You've completed '{goal.name}'! Time to celebrate your achievement!"
                }
            }
            self.websocket_manager.send_to_user(user_id, json.dumps(message))