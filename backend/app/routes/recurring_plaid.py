"""
Plaid recurring transaction insights API endpoints.
Handles Plaid's native recurring transaction detection and subscription insights.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, get_db_with_user_context
from app.dependencies import get_plaid_service, get_account_service
from app.models.user import User
from app.services.account_service import AccountService
from app.core.exceptions import (
    PlaidIntegrationError,
    ExternalServiceError,
    DataIntegrityError,
    ValidationError,
    AccountNotFoundError
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/plaid/insights",
    response_model=Dict[str, Any],
    summary="Get Plaid recurring transaction insights",
    description="Get recurring transaction insights from Plaid for connected accounts"
)
async def get_plaid_recurring_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    plaid_service = Depends(get_plaid_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Get recurring transaction insights from Plaid."""
    try:
        # Verify account ownership if account_id provided
        if account_id:
            account = account_service.get(db=db, id=account_id)
            if not account or account.user_id != current_user.id:
                raise AccountNotFoundError(str(account_id))
            
            if not account.plaid_access_token:
                raise ValidationError("Account is not connected to Plaid")
        
        insights = await plaid_service.sync_recurring_transactions_for_user(db, current_user.id)
        
        return {
            "success": True,
            "data": insights
        }
        
    except (AccountNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve Plaid recurring insights: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to retrieve recurring transaction insights")


@router.get(
    "/plaid/subscriptions",
    response_model=List[Dict[str, Any]],
    summary="Get subscription insights from Plaid",
    description="Get subscription and recurring payment insights from Plaid"
)
async def get_plaid_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    category: Optional[str] = Query(None, description="Filter by subscription category"),
    plaid_service = Depends(get_plaid_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Get subscription insights from Plaid."""
    try:
        # Verify account ownership if account_id provided
        if account_id:
            account = account_service.get(db=db, id=account_id)
            if not account or account.user_id != current_user.id:
                raise AccountNotFoundError(str(account_id))
            
            if not account.plaid_access_token:
                raise ValidationError("Account is not connected to Plaid")
        
        subscriptions = await plaid_service.get_subscription_insights(
            db, str(current_user.id),
            account_id=account_id,
            category=category
        )
        
        return subscriptions
        
    except (AccountNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve Plaid subscription insights: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to retrieve subscription insights")


@router.post(
    "/plaid/sync",
    response_model=Dict[str, Any],
    summary="Sync Plaid recurring data",
    description="Sync latest recurring transaction data from Plaid"
)
async def sync_plaid_recurring_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    account_id: Optional[UUID] = Query(None, description="Sync specific account only"),
    force_refresh: bool = Query(False, description="Force refresh even if recently synced"),
    plaid_service = Depends(get_plaid_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Sync recurring transaction data from Plaid."""
    try:
        # Verify account ownership if account_id provided
        if account_id:
            account = account_service.get(db=db, id=account_id)
            if not account or account.user_id != current_user.id:
                raise AccountNotFoundError(str(account_id))
            
            if not account.plaid_access_token:
                raise ValidationError("Account is not connected to Plaid")
        
        sync_result = await plaid_service.sync_recurring_data(
            db, str(current_user.id),
            account_id=account_id,
            force_refresh=force_refresh
        )
        
        return {
            "success": True,
            "message": "Plaid recurring data synced successfully",
            "data": sync_result
        }
        
    except (AccountNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to sync Plaid recurring data: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to sync recurring data")


@router.get(
    "/plaid/patterns",
    response_model=List[Dict[str, Any]],
    summary="Get Plaid recurring patterns",
    description="Get recurring transaction patterns detected by Plaid"
)
async def get_plaid_recurring_patterns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    confidence_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence score"),
    plaid_service = Depends(get_plaid_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Get recurring transaction patterns from Plaid."""
    try:
        # Verify account ownership if account_id provided
        if account_id:
            account = account_service.get(db=db, id=account_id)
            if not account or account.user_id != current_user.id:
                raise AccountNotFoundError(str(account_id))
            
            if not account.plaid_access_token:
                raise ValidationError("Account is not connected to Plaid")
        
        patterns = await plaid_service.get_recurring_patterns(
            db, str(current_user.id),
            account_id=account_id,
            confidence_threshold=confidence_threshold
        )
        
        return patterns
        
    except (AccountNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve Plaid recurring patterns: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to retrieve recurring patterns")


@router.get(
    "/plaid/merchant-insights",
    response_model=Dict[str, Any],
    summary="Get merchant recurring insights",
    description="Get insights about recurring transactions grouped by merchant"
)
async def get_plaid_merchant_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    merchant_name: Optional[str] = Query(None, description="Filter by merchant name"),
    min_transactions: int = Query(3, ge=2, description="Minimum number of transactions"),
    plaid_service = Depends(get_plaid_service)
):
    """Get merchant-based recurring transaction insights from Plaid."""
    try:
        insights = await plaid_service.get_merchant_recurring_insights(
            db, str(current_user.id),
            merchant_name=merchant_name,
            min_transactions=min_transactions
        )
        
        return {
            "success": True,
            "data": insights
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve merchant recurring insights: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve merchant insights")


@router.post(
    "/plaid/create-rule-from-pattern",
    response_model=Dict[str, Any],
    summary="Create rule from Plaid pattern",
    description="Create a recurring transaction rule from a Plaid-detected pattern"
)
async def create_rule_from_plaid_pattern(
    pattern_id: str,
    rule_name: str,
    category_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    plaid_service = Depends(get_plaid_service)
):
    """Create a recurring transaction rule from a Plaid-detected pattern."""
    try:
        rule = await plaid_service.create_rule_from_pattern(
            db, str(current_user.id),
            pattern_id,
            rule_name,
            category_id
        )
        
        return {
            "success": True,
            "message": "Recurring rule created from Plaid pattern",
            "rule_id": str(rule.id) if rule else None
        }
        
    except Exception as e:
        logger.error(f"Failed to create rule from Plaid pattern: {e}", exc_info=True)
        raise ValidationError("Unable to create rule from pattern")


@router.get(
    "/plaid/spending-trends",
    response_model=Dict[str, Any],
    summary="Get recurring spending trends",
    description="Get trends and analytics for recurring spending from Plaid data"
)
async def get_plaid_spending_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    period_months: int = Query(12, ge=3, le=24, description="Analysis period in months"),
    category_filter: Optional[str] = Query(None, description="Filter by category"),
    plaid_service = Depends(get_plaid_service)
):
    """Get spending trends for recurring transactions from Plaid data."""
    try:
        trends = await plaid_service.get_recurring_spending_trends(
            db, str(current_user.id),
            period_months=period_months,
            category_filter=category_filter
        )
        
        return {
            "success": True,
            "data": trends,
            "analysis_period_months": period_months
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve recurring spending trends: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve spending trends")


@router.get(
    "/plaid/upcoming-payments",
    response_model=List[Dict[str, Any]],
    summary="Get upcoming recurring payments",
    description="Get predicted upcoming recurring payments based on Plaid patterns"
)
async def get_upcoming_recurring_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    days_ahead: int = Query(30, ge=7, le=90, description="Days to look ahead"),
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    plaid_service = Depends(get_plaid_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Get predicted upcoming recurring payments."""
    try:
        # Verify account ownership if account_id provided
        if account_id:
            account = account_service.get(db=db, id=account_id)
            if not account or account.user_id != current_user.id:
                raise AccountNotFoundError(str(account_id))
        
        upcoming_payments = await plaid_service.get_upcoming_recurring_payments(
            db, str(current_user.id),
            days_ahead=days_ahead,
            account_id=account_id
        )
        
        return upcoming_payments
        
    except AccountNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve upcoming recurring payments: {e}", exc_info=True)
        raise DataIntegrityError("Unable to retrieve upcoming payments")