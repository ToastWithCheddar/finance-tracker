from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from uuid import UUID
import logging

from app.core.exceptions import CategoryNotFoundError, BudgetNotFoundError, DataIntegrityError, BusinessLogicError, ValidationError

from ..database import get_db
from app.dependencies import get_budget_service, get_owned_budget
from ..services.budget_service import BudgetService
from ..schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetFilter,
    BudgetListResponse, BudgetProgress, BudgetPeriod, BudgetCalendarResponse
)
from ..auth.dependencies import get_current_user, get_db_with_user_context
from ..models.user import User
from ..models.category import Category

router = APIRouter(tags=["budgets"])
logger = logging.getLogger(__name__)


@router.post("", response_model=BudgetResponse)
def create_budget(
    budget: BudgetCreate,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Create a new budget"""
    # Validate category exists if provided
    if budget.category_id:
        category = db.query(Category).filter(
            Category.id == budget.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise CategoryNotFoundError(str(budget.category_id))
    
    try:
        created_budget = budget_service.create_budget(db, budget, current_user.id)
    except SQLAlchemyError as e:
        logger.error(f"Database error creating budget: {str(e)}")
        raise DataIntegrityError("Failed to create budget due to database error")
    except Exception as e:
        logger.error(f"Unexpected error creating budget: {str(e)}", exc_info=True)
        raise BusinessLogicError("An error occurred while creating budget")
    
    # Calculate usage for response
    usage = budget_service.calculate_budget_usage(db, created_budget)
    
    # Refresh to get eager-loaded relationships
    db.refresh(created_budget)
    category_name = created_budget.category.name if created_budget.category else None
    
    # Check if custom alert settings exist
    has_custom_alerts = hasattr(created_budget, 'alert_settings') and created_budget.alert_settings is not None
    
    return BudgetResponse(
        id=str(created_budget.id),
        user_id=str(created_budget.user_id),
        category_id=str(created_budget.category_id) if created_budget.category_id else None,
        category_name=category_name,
        name=created_budget.name,
        amount_cents=created_budget.amount_cents,
        period=created_budget.period,
        start_date=created_budget.start_date,
        end_date=created_budget.end_date,
        alert_threshold=created_budget.alert_threshold,
        is_active=created_budget.is_active,
        created_at=created_budget.created_at,
        updated_at=created_budget.updated_at,
        usage=usage,
        has_custom_alerts=has_custom_alerts
    )


@router.get("", response_model=BudgetListResponse)
def get_budgets(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    period: Optional[BudgetPeriod] = Query(None, description="Filter by period"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    over_budget: Optional[bool] = Query(None, description="Filter over-budget items"),
    skip: int = Query(0, ge=0, description="Number of budgets to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of budgets to return"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get budgets with optional filters"""
    filters = BudgetFilter(
        category_id=category_id,
        period=period,
        is_active=is_active,
        over_budget=over_budget
    )
    
    # Use optimized method to get budgets with usage data in minimal queries
    budgets_with_usage = BudgetService.get_budgets_with_usage(db, current_user.id, filters, skip, limit)
    summary = BudgetService.get_budget_summary(db, current_user.id)
    alerts = BudgetService.get_budget_alerts(db, current_user.id)
    
    # Build response using pre-calculated usage data
    budget_responses = []
    for budget, usage in budgets_with_usage:
        # Category name is available due to eager loading
        category_name = budget.category.name if budget.category else None
        
        # Check if custom alert settings exist
        has_custom_alerts = hasattr(budget, 'alert_settings') and budget.alert_settings is not None
        
        budget_responses.append(BudgetResponse(
            id=budget.id,
            user_id=budget.user_id,
            category_id=budget.category_id,
            category_name=category_name,
            name=budget.name,
            amount_cents=budget.amount_cents,
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
            alert_threshold=budget.alert_threshold,
            is_active=budget.is_active,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
            usage=usage,
            has_custom_alerts=has_custom_alerts
        ))
    
    return BudgetListResponse(
        budgets=budget_responses,
        summary=summary,
        alerts=alerts
    )


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget = Depends(get_owned_budget),
    db: Session = Depends(get_db_with_user_context)
):
    """Get a budget by ID"""
    
    # Calculate usage
    usage = BudgetService.calculate_budget_usage(db, budget)
    
    # Category name is available due to eager loading from get_budget
    category_name = budget.category.name if budget.category else None
    
    # Check if custom alert settings exist
    has_custom_alerts = hasattr(budget, 'alert_settings') and budget.alert_settings is not None
    
    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        category_name=category_name,
        name=budget.name,
        amount_cents=budget.amount_cents,
        period=budget.period,
        start_date=budget.start_date,
        end_date=budget.end_date,
        alert_threshold=budget.alert_threshold,
        is_active=budget.is_active,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
        usage=usage,
        has_custom_alerts=has_custom_alerts
    )


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_update: BudgetUpdate,
    budget = Depends(get_owned_budget),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Update a budget"""
    
    # Validate category exists if being updated
    if budget_update.category_id:
        category = db.query(Category).filter(
            Category.id == budget_update.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise CategoryNotFoundError(str(budget_update.category_id))
    
    updated_budget = BudgetService.update_budget(db, budget, budget_update)
    
    # Calculate usage for response
    usage = BudgetService.calculate_budget_usage(db, updated_budget)
    
    # Refresh to get updated eager-loaded relationships
    db.refresh(updated_budget)
    category_name = updated_budget.category.name if updated_budget.category else None
    
    # Check if custom alert settings exist
    has_custom_alerts = hasattr(updated_budget, 'alert_settings') and updated_budget.alert_settings is not None
    
    return BudgetResponse(
        id=updated_budget.id,
        user_id=updated_budget.user_id,
        category_id=updated_budget.category_id,
        category_name=category_name,
        name=updated_budget.name,
        amount_cents=updated_budget.amount_cents,
        period=updated_budget.period,
        start_date=updated_budget.start_date,
        end_date=updated_budget.end_date,
        alert_threshold=updated_budget.alert_threshold,
        is_active=updated_budget.is_active,
        created_at=updated_budget.created_at,
        updated_at=updated_budget.updated_at,
        usage=usage,
        has_custom_alerts=has_custom_alerts
    )


@router.delete("/{budget_id}")
def delete_budget(
    budget = Depends(get_owned_budget),
    db: Session = Depends(get_db_with_user_context)
):
    """Delete a budget"""
    
    BudgetService.delete_budget(db, budget)
    return {"message": "Budget deleted successfully"}


@router.get("/{budget_id}/progress", response_model=BudgetProgress)
def get_budget_progress(
    budget = Depends(get_owned_budget),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get detailed budget progress over time"""
    progress = BudgetService.get_budget_progress(db, budget.id, current_user.id)
    if not progress:
        raise BudgetNotFoundError(str(budget.id))
    
    return progress


@router.get("/analytics/summary")
def get_budget_summary(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get budget summary statistics"""
    return BudgetService.get_budget_summary(db, current_user.id)


@router.get("/analytics/alerts")
def get_budget_alerts(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get current budget alerts"""
    return BudgetService.get_budget_alerts(db, current_user.id)


@router.get("/{budget_id}/calendar", response_model=BudgetCalendarResponse)
def get_budget_calendar(
    month: str = Query(..., description="Month in YYYY-MM format"),
    budget = Depends(get_owned_budget),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get budget calendar data for a specific month"""
    try:
        calendar_data = BudgetService.get_budget_calendar(db, budget.id, current_user.id, month)
        if not calendar_data:
            raise BudgetNotFoundError(str(budget.id))
        
        return calendar_data
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Error getting budget calendar: {e}", exc_info=True)
        raise BusinessLogicError("An error occurred while retrieving budget calendar")