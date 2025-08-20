# Standard library imports
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

# Third-party imports
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

# Local imports
from app.database import get_db
from app.auth.dependencies import get_current_user, get_db_with_user_context
from app.models.user import User
from app.models.categorization_rule import CategorizationRule
from app.models.categorization_rule_template import CategorizationRuleTemplate
from app.models.transaction import Transaction
from app.services.auto_categorization_service import AutoCategorizationService
from app.services.rule_template_service import RuleTemplateService
from app.schemas.categorization_rule import (
    CategorizationRuleCreate,
    CategorizationRuleUpdate,
    CategorizationRuleResponse,
    CategorizationRuleFilter,
    PaginatedCategorizationRulesResponse,
    RuleTestResponse,
    RuleApplicationResponse,
    RuleEffectivenessResponse,
    RuleStatisticsResponse,
    RuleFeedbackResponse,
    RuleTemplateResponse,
    RuleTemplateCreateResponse
)
from app.core.exceptions import (
    ValidationError,
    CategorizationRuleNotFoundError,
    DuplicateResourceError,
    DataIntegrityError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/categorization-rules",
    tags=["categorization-rules"]
)

@router.post(
    "/",
    summary="Create a categorization rule",
    description="Create a new categorization rule for automatic transaction categorization",
    response_model=CategorizationRuleResponse
)
async def create_categorization_rule(
    rule_data: CategorizationRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Create a new categorization rule."""
    try:
        # Create the rule
        rule = CategorizationRule(
            user_id=current_user.id,
            name=rule_data.name,
            description=rule_data.description,
            priority=rule_data.priority,
            conditions=rule_data.conditions.dict(),
            actions=rule_data.actions.dict(),
            template_id=rule_data.template_id,
            template_version=rule_data.template_version,
            is_active=rule_data.is_active
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return rule
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create categorization rule for user {current_user.id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to create categorization rule")

@router.get(
    "/",
    summary="Get categorization rules",
    description="Get user's categorization rules with filtering and pagination",
    response_model=PaginatedCategorizationRulesResponse
)
async def get_categorization_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    filters: CategorizationRuleFilter = Depends()
):
    """Get user's categorization rules with filtering and pagination."""
    try:
        # Build query
        query = db.query(CategorizationRule).filter(
            CategorizationRule.user_id == current_user.id
        )
        
        # Apply filters
        if filters.is_active is not None:
            query = query.filter(CategorizationRule.is_active == filters.is_active)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    CategorizationRule.name.ilike(search_term),
                    CategorizationRule.description.ilike(search_term)
                )
            )
        
        if filters.priority_min is not None:
            query = query.filter(CategorizationRule.priority >= filters.priority_min)
        
        if filters.priority_max is not None:
            query = query.filter(CategorizationRule.priority <= filters.priority_max)
        
        if filters.template_id is not None:
            query = query.filter(CategorizationRule.template_id == filters.template_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        rules = query.order_by(CategorizationRule.priority.asc())\
                    .offset(filters.offset)\
                    .limit(filters.limit)\
                    .all()
        
        # Calculate pagination values
        has_more = total > filters.offset + len(rules)
        
        return PaginatedCategorizationRulesResponse(
            items=rules,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch categorization rules for user {current_user.id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve categorization rules")

@router.get(
    "/{rule_id}",
    summary="Get a specific categorization rule",
    description="Get details of a specific categorization rule",
    response_model=CategorizationRuleResponse
)
async def get_categorization_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get a specific categorization rule."""
    rule = db.query(CategorizationRule).filter(
        and_(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise CategorizationRuleNotFoundError(str(rule_id))
    
    return rule

@router.put(
    "/{rule_id}",
    summary="Update a categorization rule",
    description="Update an existing categorization rule",
    response_model=CategorizationRuleResponse
)
async def update_categorization_rule(
    rule_id: UUID,
    rule_update: CategorizationRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Update an existing categorization rule."""
    rule = db.query(CategorizationRule).filter(
        and_(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise CategorizationRuleNotFoundError(str(rule_id))
    
    try:
        # Update fields if provided
        update_data = rule_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field in ["conditions", "actions"] and value is not None:
                setattr(rule, field, value.dict())
            else:
                setattr(rule, field, value)
        
        # Clear cache when rules are updated
        auto_categorization_service = AutoCategorizationService(db)
        auto_categorization_service.clear_rule_cache(current_user.id)
        
        db.commit()
        db.refresh(rule)
        
        return rule
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update categorization rule {rule_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to update categorization rule")

@router.delete(
    "/{rule_id}",
    summary="Delete a categorization rule",
    description="Delete an existing categorization rule"
)
async def delete_categorization_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Delete a categorization rule."""
    rule = db.query(CategorizationRule).filter(
        and_(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise CategorizationRuleNotFoundError(str(rule_id))
    
    try:
        db.delete(rule)
        
        # Clear cache when rules are deleted
        auto_categorization_service = AutoCategorizationService(db)
        auto_categorization_service.clear_rule_cache(current_user.id)
        
        db.commit()
        
        return {"success": True, "message": "Rule deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete categorization rule {rule_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to delete categorization rule")

@router.post(
    "/{rule_id}/test",
    summary="Test categorization rule",
    description="Test rule against historical transactions to see what would match",
    response_model=RuleTestResponse
)
async def test_categorization_rule(
    rule_id: UUID,
    limit: int = Query(100, ge=1, le=500, description="Number of transactions to test against"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Test rule against historical transactions."""
    rule = db.query(CategorizationRule).filter(
        and_(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise CategorizationRuleNotFoundError(str(rule_id))
    
    try:
        auto_categorization_service = AutoCategorizationService(db)
        
        matching_transactions = auto_categorization_service.test_rule_against_transactions(
            rule_conditions=rule.conditions,
            user_id=current_user.id,
            limit=limit
        )
        
        return RuleTestResponse(
            rule_id=rule.id,
            rule_name=rule.name,
            total_matches=len(matching_transactions),
            matching_transactions=matching_transactions
        )
        
    except Exception as e:
        logger.error(f"Failed to test categorization rule {rule_id}: {e}", exc_info=True)
        raise BusinessLogicError("Unable to test categorization rule")

@router.post(
    "/test-conditions",
    summary="Test rule conditions",
    description="Test rule conditions against historical transactions without saving a rule",
    response_model=RuleTestResponse
)
async def test_rule_conditions(
    conditions: Dict[str, Any],
    limit: int = Query(100, ge=1, le=500, description="Number of transactions to test against"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Test rule conditions against historical transactions."""
    try:
        auto_categorization_service = AutoCategorizationService(db)
        
        matching_transactions = auto_categorization_service.test_rule_against_transactions(
            rule_conditions=conditions,
            user_id=current_user.id,
            limit=limit
        )
        
        return RuleTestResponse(
            conditions=conditions,
            total_matches=len(matching_transactions),
            matching_transactions=matching_transactions
        )
        
    except Exception as e:
        logger.error(f"Failed to test rule conditions: {e}", exc_info=True)
        raise BusinessLogicError("Unable to test rule conditions")

@router.post(
    "/apply-to-transactions",
    summary="Apply rules to transactions",
    description="Apply categorization rules to specific transactions",
    response_model=RuleApplicationResponse
)
async def apply_rules_to_transactions(
    transaction_ids: List[UUID],
    dry_run: bool = Query(False, description="Preview changes without applying them"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Apply categorization rules to specific transactions."""
    try:
        auto_categorization_service = AutoCategorizationService(db)
        
        result = auto_categorization_service.batch_apply_rules(
            transaction_ids=transaction_ids,
            user_id=current_user.id,
            dry_run=dry_run
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to apply rules to transactions for user {current_user.id}: {e}", exc_info=True)
        raise BusinessLogicError("Unable to apply rules to transactions")

@router.get(
    "/templates",
    summary="Get rule templates",
    description="Get available categorization rule templates",
    response_model=List[RuleTemplateResponse]
)
async def get_rule_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    category_filter: Optional[str] = Query(None, description="Filter by category"),
    official_only: bool = Query(False, description="Show only official templates"),
    limit: int = Query(50, ge=1, le=100, description="Number of templates to return")
):
    """Get available rule templates."""
    try:
        template_service = RuleTemplateService(db)
        
        if official_only:
            templates = template_service.get_official_templates(category_filter)
        else:
            templates = template_service.get_popular_templates(limit, category_filter)
        
        return templates
        
    except Exception as e:
        logger.error(f"Failed to fetch rule templates: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve rule templates")

@router.post(
    "/templates/{template_id}/create-rule",
    summary="Create rule from template",
    description="Create a categorization rule from a template",
    response_model=RuleTemplateCreateResponse
)
async def create_rule_from_template(
    template_id: UUID,
    customizations: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Create a categorization rule from a template."""
    try:
        template_service = RuleTemplateService(db)
        
        rule = template_service.create_rule_from_template(
            template_id=template_id,
            user_id=current_user.id,
            customizations=customizations
        )
        
        # Clear cache after creating new rule
        auto_categorization_service = AutoCategorizationService(db)
        auto_categorization_service.clear_rule_cache(current_user.id)
        
        return RuleTemplateCreateResponse(
            success=True,
            rule_id=rule.id,
            rule_name=rule.name,
            template_id=template_id,
            created_at=rule.created_at
        )
        
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to create rule from template: {e}", exc_info=True)
        raise DataIntegrityError("Unable to create rule from template")

@router.get(
    "/statistics",
    summary="Get rule statistics",
    description="Get statistics about user's categorization rules",
    response_model=RuleStatisticsResponse
)
async def get_rule_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get statistics about user's categorization rules."""
    try:
        auto_categorization_service = AutoCategorizationService(db)
        
        statistics = auto_categorization_service.get_matching_statistics(current_user.id)
        
        return statistics
        
    except Exception as e:
        logger.error(f"Failed to fetch rule statistics for user {current_user.id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve rule statistics")

@router.get(
    "/{rule_id}/effectiveness",
    summary="Get rule effectiveness",
    description="Get effectiveness metrics for a specific rule",
    response_model=RuleEffectivenessResponse
)
async def get_rule_effectiveness(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get effectiveness metrics for a specific rule."""
    try:
        auto_categorization_service = AutoCategorizationService(db)
        
        effectiveness = auto_categorization_service.get_rule_effectiveness(
            rule_id=rule_id,
            user_id=current_user.id
        )
        
        if "error" in effectiveness:
            raise CategorizationRuleNotFoundError(str(rule_id))
        
        return effectiveness
        
    except CategorizationRuleNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch rule effectiveness for rule {rule_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve rule effectiveness")

@router.post(
    "/{rule_id}/feedback",
    summary="Provide rule feedback",
    description="Provide feedback on rule effectiveness",
    response_model=RuleFeedbackResponse
)
async def provide_rule_feedback(
    rule_id: UUID,
    success: bool = Query(..., description="Whether the rule application was successful"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Provide feedback on rule effectiveness."""
    rule = db.query(CategorizationRule).filter(
        and_(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == current_user.id
        )
    ).first()
    
    if not rule:
        raise CategorizationRuleNotFoundError(str(rule_id))
    
    try:
        rule.update_success_rate(success)
        db.add(rule)
        db.commit()
        
        return RuleFeedbackResponse(
            success=True,
            rule_id=rule.id,
            new_success_rate=rule.success_rate,
            new_success_rate_percentage=rule.success_rate_percentage
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update rule feedback for rule {rule_id}: {e}", exc_info=True)
        raise DataIntegrityError("Unable to update rule feedback")