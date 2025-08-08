from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID

from ..database import get_db
from ..services.budget_service import BudgetService
from ..schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetFilter,
    BudgetListResponse, BudgetProgress, BudgetPeriod
)
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..models.category import Category

router = APIRouter(tags=["budgets"])


@router.post("", response_model=BudgetResponse)
def create_budget(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new budget"""
    # Validate category exists if provided
    if budget.category_id:
        category = db.query(Category).filter(
            Category.id == budget.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    created_budget = BudgetService.create_budget(db, budget, current_user.id)
    
    # Calculate usage for response
    usage = BudgetService.calculate_budget_usage(db, created_budget)
    
    # Get category name if applicable
    category_name = None
    if created_budget.category_id:
        category = db.query(Category).filter(Category.id == created_budget.category_id).first()
        category_name = category.name if category else None
    
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
        usage=usage
    )


@router.get("", response_model=BudgetListResponse)
def get_budgets(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    period: Optional[BudgetPeriod] = Query(None, description="Filter by period"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    over_budget: Optional[bool] = Query(None, description="Filter over-budget items"),
    skip: int = Query(0, ge=0, description="Number of budgets to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of budgets to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get budgets with optional filters"""
    filters = BudgetFilter(
        category_id=category_id,
        period=period,
        is_active=is_active,
        over_budget=over_budget
    )
    
    budgets = BudgetService.get_budgets(db, current_user.id, filters, skip, limit)
    summary = BudgetService.get_budget_summary(db, current_user.id)
    alerts = BudgetService.get_budget_alerts(db, current_user.id)
    
    # Build response with usage data
    budget_responses = []
    for budget in budgets:
        usage = BudgetService.calculate_budget_usage(db, budget)
        
        # Apply over_budget filter if specified
        if over_budget is not None and usage.is_over_budget != over_budget:
            continue
        
        # Get category name if applicable
        category_name = None
        if budget.category_id:
            category = db.query(Category).filter(Category.id == budget.category_id).first()
            category_name = category.name if category else None
        
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
            usage=usage
        ))
    
    return BudgetListResponse(
        budgets=budget_responses,
        summary=summary,
        alerts=alerts
    )


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a budget by ID"""
    budget = BudgetService.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    # Calculate usage
    usage = BudgetService.calculate_budget_usage(db, budget)
    
    # Get category name if applicable
    category_name = None
    if budget.category_id:
        category = db.query(Category).filter(Category.id == budget.category_id).first()
        category_name = category.name if category else None
    
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
        usage=usage
    )


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: UUID,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a budget"""
    budget = BudgetService.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    # Validate category exists if being updated
    if budget_update.category_id:
        category = db.query(Category).filter(
            Category.id == budget_update.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    updated_budget = BudgetService.update_budget(db, budget, budget_update)
    
    # Calculate usage for response
    usage = BudgetService.calculate_budget_usage(db, updated_budget)
    
    # Get category name if applicable
    category_name = None
    if updated_budget.category_id:
        category = db.query(Category).filter(Category.id == updated_budget.category_id).first()
        category_name = category.name if category else None
    
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
        usage=usage
    )


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a budget"""
    budget = BudgetService.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    BudgetService.delete_budget(db, budget)
    return {"message": "Budget deleted successfully"}


@router.get("/{budget_id}/progress", response_model=BudgetProgress)
def get_budget_progress(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed budget progress over time"""
    progress = BudgetService.get_budget_progress(db, budget_id, current_user.id)
    if not progress:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    return progress


@router.get("/analytics/summary")
def get_budget_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get budget summary statistics"""
    return BudgetService.get_budget_summary(db, current_user.id)


@router.get("/analytics/alerts")
def get_budget_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current budget alerts"""
    return BudgetService.get_budget_alerts(db, current_user.id)