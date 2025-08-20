from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..auth.dependencies import get_current_user, get_db_with_user_context
from ..schemas.goal import (
    Goal, GoalCreate, GoalUpdate, GoalContribution, GoalContributionCreate,
    GoalsResponse, GoalStats, GoalStatus, GoalType, GoalPriority
)
from app.dependencies import get_goal_service, get_owned_goal
from ..services.goal_service import GoalService
from uuid import UUID

router = APIRouter(prefix="/goals", tags=["goals"])

@router.post("/", response_model=Goal)
async def create_goal(
    goal_data: GoalCreate,
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Create a new financial goal"""
    return goal_service.create_goal(db, current_user["id"], goal_data)

@router.get("/", response_model=GoalsResponse)
async def get_goals(
    status: Optional[GoalStatus] = Query(None, description="Filter by goal status"),
    goal_type: Optional[GoalType] = Query(None, description="Filter by goal type"),
    priority: Optional[GoalPriority] = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0, description="Number of goals to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of goals to return"),
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Get user's financial goals with filtering and statistics"""
    return goal_service.get_goals(
        db, current_user["id"], status, goal_type, priority, skip, limit
    )

@router.get("/stats", response_model=GoalStats)
async def get_goal_statistics(
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Get comprehensive goal statistics and analytics"""
    return goal_service.get_goal_stats(db, current_user["id"])

@router.get("/{goal_id}", response_model=Goal)
async def get_goal(
    goal = Depends(get_owned_goal)
):
    """Get a specific goal with all related data"""
    return goal

@router.put("/{goal_id}", response_model=Goal)
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Update an existing goal"""
    goal = goal_service.update_goal(db, current_user["id"], goal_id, goal_data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Delete a goal and all related data"""
    success = goal_service.delete_goal(db, current_user["id"], goal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted successfully"}

@router.post("/{goal_id}/contributions", response_model=GoalContribution)
async def add_contribution(
    goal_id: UUID,
    contribution_data: GoalContributionCreate,
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Add a contribution to a goal"""
    contribution = goal_service.add_contribution(
        db, current_user["id"], goal_id, contribution_data
    )
    if not contribution:
        raise HTTPException(
            status_code=404, 
            detail="Goal not found or not available for contributions"
        )
    return contribution

@router.get("/{goal_id}/contributions", response_model=List[GoalContribution])
async def get_goal_contributions(
    goal_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Get contributions for a specific goal"""
    goal = goal_service.get_goal(db, current_user["id"], goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    contributions = goal.contributions[skip:skip+limit] if goal.contributions else []
    return contributions

@router.post("/process-auto-contributions")
async def process_automatic_contributions(
    # BackgroundTasks is a FastAPI dependency that allows us to run tasks in the background
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_with_user_context),
    current_user: dict = Depends(get_current_user),
    goal_service: GoalService = Depends(get_goal_service)
):
    """Process automatic contributions (admin/system endpoint)"""
    # This would typically be called by a scheduled job
    # For demo purposes, allowing manual trigger
    result = goal_service.process_automatic_contributions(db)
    return {
        "message": "Automatic contributions processed",
        "results": result
    }

@router.get("/types/options")
async def get_goal_type_options():
    """Get available goal types and priorities for UI dropdowns"""
    return {
        "goal_types": [
            {"value": "savings", "label": "Savings", "icon": "💰"},
            {"value": "debt_payoff", "label": "Debt Payoff", "icon": "💳"},
            {"value": "emergency_fund", "label": "Emergency Fund", "icon": "🚨"},
            {"value": "investment", "label": "Investment", "icon": "📈"},
            {"value": "purchase", "label": "Purchase", "icon": "🛍️"},
            {"value": "other", "label": "Other", "icon": "🎯"}
        ],
        "priorities": [
            {"value": "low", "label": "Low", "color": "gray"},
            {"value": "medium", "label": "Medium", "color": "blue"},
            {"value": "high", "label": "High", "color": "orange"},
            {"value": "critical", "label": "Critical", "color": "red"}
        ],
        "frequencies": [
            {"value": "daily", "label": "Daily"},
            {"value": "weekly", "label": "Weekly"},
            {"value": "monthly", "label": "Monthly"},
            {"value": "custom", "label": "Custom"}
        ]
    }