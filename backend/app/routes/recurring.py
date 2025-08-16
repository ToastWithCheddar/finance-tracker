# Standard library imports
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

# Local imports
from app.database import get_db
from app.auth.dependencies import get_current_user, get_db_with_user_context
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransactionRule, FrequencyType
from app.schemas.recurring_transaction import (
    RecurringTransactionRuleCreate,
    RecurringTransactionRuleUpdate, 
    RecurringTransactionRuleResponse,
    RecurringSuggestion,
    SuggestionApproval,
    RecurringRuleFilter,
    PaginatedRecurringRulesResponse,
    RecurringRuleStats,
    RecurringTransactionError
)
from app.services.recurring_detection_service import RecurringDetectionService

# Create router
router = APIRouter(
    prefix="/api/recurring",
    tags=["recurring-transactions"]
)

def _validate_recurring_rule(
    rule_data: RecurringTransactionRuleCreate | RecurringTransactionRuleUpdate, 
    db: Session, 
    user_id: UUID,
    existing_rule: Optional[RecurringTransactionRule] = None
) -> List[str]:
    """
    Validate recurring rule data and return list of error messages.
    
    Args:
        rule_data: The rule data to validate
        db: Database session
        user_id: Current user ID
        existing_rule: Existing rule for updates (None for creates)
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # For updates, use existing values when not provided
    if isinstance(rule_data, RecurringTransactionRuleUpdate) and existing_rule:
        account_id = rule_data.account_id or existing_rule.account_id
        category_id = rule_data.category_id or existing_rule.category_id
        amount_cents = rule_data.amount_cents or existing_rule.amount_cents
        frequency = rule_data.frequency or existing_rule.frequency
        interval = rule_data.interval or existing_rule.interval
        start_date = existing_rule.start_date  # Start date shouldn't change in updates
        end_date = rule_data.end_date if hasattr(rule_data, 'end_date') else existing_rule.end_date
    else:
        account_id = rule_data.account_id
        category_id = getattr(rule_data, 'category_id', None)
        amount_cents = rule_data.amount_cents
        frequency = rule_data.frequency
        interval = rule_data.interval
        start_date = rule_data.start_date
        end_date = getattr(rule_data, 'end_date', None)
    
    # Validate account exists and belongs to user
    if account_id:
        account = db.query(Account).filter(
            and_(Account.id == account_id, Account.user_id == user_id)
        ).first()
        if not account:
            errors.append("Invalid account ID or account does not belong to user")
    
    # Validate category exists and belongs to user (if provided)
    if category_id:
        category = db.query(Category).filter(
            and_(Category.id == category_id, Category.user_id == user_id)
        ).first()
        if not category:
            errors.append("Invalid category ID or category does not belong to user")
    
    # Validate amount
    if amount_cents is not None and amount_cents <= 0:
        errors.append("Amount must be greater than 0")
    
    # Validate frequency and interval
    if frequency and interval:
        if frequency == FrequencyType.WEEKLY and interval > 52:
            errors.append("Weekly interval cannot exceed 52 weeks")
        elif frequency == FrequencyType.MONTHLY and interval > 12:
            errors.append("Monthly interval cannot exceed 12 months")
        elif frequency == FrequencyType.QUARTERLY and interval > 4:
            errors.append("Quarterly interval cannot exceed 4 quarters")
        elif frequency == FrequencyType.ANNUALLY and interval > 10:
            errors.append("Annual interval cannot exceed 10 years")
    
    # Validate date range
    if start_date and end_date and end_date <= start_date:
        errors.append("End date must be after start date")
    
    # Check for duplicate rules (same account, similar amount, same frequency)
    if account_id and amount_cents and frequency:
        tolerance = max(int(amount_cents * 0.1), 100)  # 10% tolerance or $1 minimum
        
        query = db.query(RecurringTransactionRule).filter(
            and_(
                RecurringTransactionRule.user_id == user_id,
                RecurringTransactionRule.account_id == account_id,
                RecurringTransactionRule.frequency == frequency,
                func.abs(RecurringTransactionRule.amount_cents - amount_cents) <= tolerance,
                RecurringTransactionRule.is_active == True
            )
        )
        
        # Exclude existing rule from check for updates
        if existing_rule:
            query = query.filter(RecurringTransactionRule.id != existing_rule.id)
        
        duplicate = query.first()
        if duplicate:
            errors.append(f"A similar recurring rule already exists: {duplicate.name}")
    
    return errors

@router.get(
    "/suggestions",
    response_model=List[RecurringSuggestion],
    summary="Get recurring transaction suggestions",
    description="Analyze transaction history and return suggestions for recurring transactions"
)
async def get_recurring_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence score")
):
    """Get recurring transaction suggestions for the current user."""
    try:
        detection_service = RecurringDetectionService(db)
        suggestions = detection_service.get_suggestions_for_user(current_user.id)
        
        # Filter by minimum confidence
        filtered_suggestions = [
            s for s in suggestions 
            if s.get('confidence_score', 0) >= min_confidence
        ]
        
        return filtered_suggestions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating suggestions: {str(e)}"
        )

@router.post(
    "/suggestions/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a recurring transaction suggestion",
    description="Mark a suggestion as dismissed so it won't appear again"
)
async def dismiss_suggestion(
    suggestion_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Dismiss a suggestion permanently."""
    try:
        detection_service = RecurringDetectionService(db)
        
        # For now, we'll just return success. In a full implementation,
        # we'd store dismissed suggestions in a separate table
        # This is a placeholder for the dismiss functionality
        
        return None
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error dismissing suggestion: {str(e)}"
        )

@router.post(
    "/suggestions/approve",
    response_model=RecurringTransactionRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Approve a recurring transaction suggestion",
    description="Convert a suggestion into an active recurring transaction rule"
)
async def approve_suggestion(
    approval: SuggestionApproval,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Approve a suggestion and create a recurring transaction rule."""
    try:
        detection_service = RecurringDetectionService(db)
        
        # Get the original suggestion
        suggestions = detection_service.get_suggestions_for_user(current_user.id)
        suggestion = next((s for s in suggestions if s['id'] == approval.suggestion_id), None)
        
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found"
            )
        
        # Apply any overrides from the approval
        if approval.name:
            suggestion['merchant'] = approval.name
        if approval.category_id:
            suggestion['category_id'] = approval.category_id
        if approval.amount_cents:
            suggestion['amount_cents'] = approval.amount_cents
        if approval.tolerance_cents is not None:
            suggestion['tolerance_cents'] = approval.tolerance_cents
        if approval.auto_categorize is not None:
            suggestion['auto_categorize'] = approval.auto_categorize
        if approval.generate_notifications is not None:
            suggestion['generate_notifications'] = approval.generate_notifications
        
        # Create the rule
        rule = detection_service.create_rule_from_suggestion(current_user.id, suggestion)
        
        return RecurringTransactionRuleResponse.from_orm(rule)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving suggestion: {str(e)}"
        )

@router.post(
    "/rules",
    response_model=RecurringTransactionRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recurring transaction rule",
    description="Create a new recurring transaction rule manually"
)
async def create_recurring_rule(
    rule_data: RecurringTransactionRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Create a new recurring transaction rule."""
    try:
        # Validate the rule data
        validation_errors = _validate_recurring_rule(rule_data, db, current_user.id)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": validation_errors}
            )
        
        # Calculate next due date
        next_due_date = rule_data.start_date
        
        rule = RecurringTransactionRule(
            user_id=current_user.id,
            account_id=rule_data.account_id,
            category_id=rule_data.category_id,
            name=rule_data.name,
            description=rule_data.description,
            amount_cents=rule_data.amount_cents,
            currency=rule_data.currency,
            frequency=rule_data.frequency,
            interval=rule_data.interval,
            start_date=rule_data.start_date,
            end_date=rule_data.end_date,
            next_due_date=next_due_date,
            tolerance_cents=rule_data.tolerance_cents,
            auto_categorize=rule_data.auto_categorize,
            generate_notifications=rule_data.generate_notifications,
            is_active=True,
            is_confirmed=True,
            detection_method="user_created",
            custom_rule=rule_data.custom_rule,
            notification_settings=rule_data.notification_settings
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return RecurringTransactionRuleResponse.from_orm(rule)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating recurring rule: {str(e)}"
        )

@router.get(
    "/rules",
    response_model=PaginatedRecurringRulesResponse,
    summary="Get recurring transaction rules",
    description="Get paginated list of user's recurring transaction rules with filtering"
)
async def get_recurring_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_confirmed: Optional[bool] = Query(None, description="Filter by confirmed status"),
    frequency: Optional[FrequencyType] = Query(None, description="Filter by frequency"),
    account_id: Optional[UUID] = Query(None, description="Filter by account"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, max_length=200, description="Search in name/description"),
    next_due_from: Optional[date] = Query(None, description="Filter by next due date from"),
    next_due_to: Optional[date] = Query(None, description="Filter by next due date to")
):
    """Get paginated list of recurring transaction rules with filtering."""
    try:
        # Build query
        query = db.query(RecurringTransactionRule).filter(
            RecurringTransactionRule.user_id == current_user.id
        )
        
        # Apply filters
        if is_active is not None:
            query = query.filter(RecurringTransactionRule.is_active == is_active)
        
        if is_confirmed is not None:
            query = query.filter(RecurringTransactionRule.is_confirmed == is_confirmed)
        
        if frequency is not None:
            query = query.filter(RecurringTransactionRule.frequency == frequency)
        
        if account_id is not None:
            query = query.filter(RecurringTransactionRule.account_id == account_id)
        
        if category_id is not None:
            query = query.filter(RecurringTransactionRule.category_id == category_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    RecurringTransactionRule.name.ilike(search_term),
                    RecurringTransactionRule.description.ilike(search_term)
                )
            )
        
        if next_due_from:
            query = query.filter(RecurringTransactionRule.next_due_date >= next_due_from)
        
        if next_due_to:
            query = query.filter(RecurringTransactionRule.next_due_date <= next_due_to)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        rules = query.order_by(desc(RecurringTransactionRule.next_due_date))\
                    .offset((page - 1) * per_page)\
                    .limit(per_page)\
                    .all()
        
        # Calculate summary statistics
        active_rules = db.query(RecurringTransactionRule).filter(
            and_(
                RecurringTransactionRule.user_id == current_user.id,
                RecurringTransactionRule.is_active == True
            )
        ).count()
        
        # Calculate upcoming in week
        week_from_now = date.today() + datetime.timedelta(days=7)
        upcoming_in_week = db.query(RecurringTransactionRule).filter(
            and_(
                RecurringTransactionRule.user_id == current_user.id,
                RecurringTransactionRule.is_active == True,
                RecurringTransactionRule.next_due_date <= week_from_now,
                RecurringTransactionRule.next_due_date >= date.today()
            )
        ).count()
        
        # Calculate total monthly amount (approximate)
        monthly_rules = db.query(RecurringTransactionRule).filter(
            and_(
                RecurringTransactionRule.user_id == current_user.id,
                RecurringTransactionRule.is_active == True
            )
        ).all()
        
        total_monthly_amount_cents = 0
        for rule in monthly_rules:
            if rule.frequency == FrequencyType.WEEKLY:
                # Calculate annual cost: 52 weeks per year, then divide by 12 for monthly average
                annual_amount = (rule.amount_cents * 52) // rule.interval
                total_monthly_amount_cents += annual_amount // 12
            elif rule.frequency == FrequencyType.BIWEEKLY:
                # Calculate annual cost: 26 biweekly periods per year, then divide by 12 for monthly average
                annual_amount = (rule.amount_cents * 26) // rule.interval
                total_monthly_amount_cents += annual_amount // 12
            elif rule.frequency == FrequencyType.MONTHLY:
                total_monthly_amount_cents += rule.amount_cents // rule.interval
            elif rule.frequency == FrequencyType.QUARTERLY:
                # Quarterly: divide by 3 months
                total_monthly_amount_cents += rule.amount_cents // (3 * rule.interval)
            elif rule.frequency == FrequencyType.ANNUALLY:
                # Annually: divide by 12 months
                total_monthly_amount_cents += rule.amount_cents // (12 * rule.interval)
        
        return PaginatedRecurringRulesResponse(
            items=[RecurringTransactionRuleResponse.from_orm(rule) for rule in rules],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page,
            active_rules=active_rules,
            upcoming_in_week=upcoming_in_week,
            total_monthly_amount_cents=total_monthly_amount_cents
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recurring rules: {str(e)}"
        )

@router.get(
    "/rules/{rule_id}",
    response_model=RecurringTransactionRuleResponse,
    summary="Get a specific recurring rule",
    description="Get details of a specific recurring transaction rule"
)
async def get_recurring_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get a specific recurring transaction rule."""
    rule = db.query(RecurringTransactionRule).filter(
        and_(
            RecurringTransactionRule.id == rule_id,
            RecurringTransactionRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring rule not found"
        )
    
    return RecurringTransactionRuleResponse.from_orm(rule)

@router.put(
    "/rules/{rule_id}",
    response_model=RecurringTransactionRuleResponse,
    summary="Update a recurring rule",
    description="Update an existing recurring transaction rule"
)
async def update_recurring_rule(
    rule_id: UUID,
    rule_update: RecurringTransactionRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Update an existing recurring transaction rule."""
    rule = db.query(RecurringTransactionRule).filter(
        and_(
            RecurringTransactionRule.id == rule_id,
            RecurringTransactionRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring rule not found"
        )
    
    try:
        # Validate the rule update
        validation_errors = _validate_recurring_rule(rule_update, db, current_user.id, rule)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": validation_errors}
            )
        
        # Update fields
        update_data = rule_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        
        # Recalculate next due date if frequency or interval changed
        if 'frequency' in update_data or 'interval' in update_data or 'next_due_date' in update_data:
            if 'next_due_date' not in update_data:
                rule.next_due_date = rule.calculate_next_due_date()
        
        db.commit()
        db.refresh(rule)
        
        return RecurringTransactionRuleResponse.from_orm(rule)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating recurring rule: {str(e)}"
        )

@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recurring rule",
    description="Delete an existing recurring transaction rule"
)
async def delete_recurring_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Delete a recurring transaction rule."""
    rule = db.query(RecurringTransactionRule).filter(
        and_(
            RecurringTransactionRule.id == rule_id,
            RecurringTransactionRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring rule not found"
        )
    
    try:
        db.delete(rule)
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting recurring rule: {str(e)}"
        )

@router.get(
    "/stats",
    response_model=RecurringRuleStats,
    summary="Get recurring rules statistics",
    description="Get summary statistics about user's recurring transaction rules"
)
async def get_recurring_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get statistics about recurring transaction rules."""
    try:
        base_query = db.query(RecurringTransactionRule).filter(
            RecurringTransactionRule.user_id == current_user.id
        )
        
        total_rules = base_query.count()
        active_rules = base_query.filter(RecurringTransactionRule.is_active == True).count()
        inactive_rules = total_rules - active_rules
        confirmed_rules = base_query.filter(RecurringTransactionRule.is_confirmed == True).count()
        suggested_rules = total_rules - confirmed_rules
        
        # Count by frequency
        weekly_count = base_query.filter(RecurringTransactionRule.frequency == FrequencyType.WEEKLY).count()
        monthly_count = base_query.filter(RecurringTransactionRule.frequency == FrequencyType.MONTHLY).count()
        quarterly_count = base_query.filter(RecurringTransactionRule.frequency == FrequencyType.QUARTERLY).count()
        annual_count = base_query.filter(RecurringTransactionRule.frequency == FrequencyType.ANNUALLY).count()
        
        # Financial statistics
        active_rules_list = base_query.filter(RecurringTransactionRule.is_active == True).all()
        total_monthly_amount_cents = 0
        total_amount = 0
        
        for rule in active_rules_list:
            total_amount += rule.amount_cents
            
            # Convert to monthly equivalent using annual calculation method
            if rule.frequency == FrequencyType.WEEKLY:
                # Calculate annual cost: 52 weeks per year, then divide by 12 for monthly average
                annual_amount = (rule.amount_cents * 52) // rule.interval
                total_monthly_amount_cents += annual_amount // 12
            elif rule.frequency == FrequencyType.BIWEEKLY:
                # Calculate annual cost: 26 biweekly periods per year, then divide by 12 for monthly average
                annual_amount = (rule.amount_cents * 26) // rule.interval
                total_monthly_amount_cents += annual_amount // 12
            elif rule.frequency == FrequencyType.MONTHLY:
                total_monthly_amount_cents += rule.amount_cents // rule.interval
            elif rule.frequency == FrequencyType.QUARTERLY:
                # Quarterly: divide by 3 months
                total_monthly_amount_cents += rule.amount_cents // (3 * rule.interval)
            elif rule.frequency == FrequencyType.ANNUALLY:
                # Annually: divide by 12 months
                total_monthly_amount_cents += rule.amount_cents // (12 * rule.interval)
        
        average_amount = int(total_amount / len(active_rules_list)) if active_rules_list else 0
        
        # Upcoming statistics
        today = date.today()
        week_from_now = today + datetime.timedelta(days=7)
        two_weeks_from_now = today + datetime.timedelta(days=14)
        
        due_this_week = base_query.filter(
            and_(
                RecurringTransactionRule.is_active == True,
                RecurringTransactionRule.next_due_date >= today,
                RecurringTransactionRule.next_due_date <= week_from_now
            )
        ).count()
        
        due_next_week = base_query.filter(
            and_(
                RecurringTransactionRule.is_active == True,
                RecurringTransactionRule.next_due_date > week_from_now,
                RecurringTransactionRule.next_due_date <= two_weeks_from_now
            )
        ).count()
        
        overdue = base_query.filter(
            and_(
                RecurringTransactionRule.is_active == True,
                RecurringTransactionRule.next_due_date < today
            )
        ).count()
        
        return RecurringRuleStats(
            total_rules=total_rules,
            active_rules=active_rules,
            inactive_rules=inactive_rules,
            confirmed_rules=confirmed_rules,
            suggested_rules=suggested_rules,
            weekly_count=weekly_count,
            monthly_count=monthly_count,
            quarterly_count=quarterly_count,
            annual_count=annual_count,
            total_monthly_amount_cents=total_monthly_amount_cents,
            average_amount_cents=average_amount,
            due_this_week=due_this_week,
            due_next_week=due_next_week,
            overdue=overdue
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recurring statistics: {str(e)}"
        )