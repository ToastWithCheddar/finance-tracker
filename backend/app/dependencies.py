"""
Central dependency injection for all services across the application.
Ensures consistent service instantiation patterns and makes testing easier.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService
from app.services.category_service import CategoryService
from app.services.budget_service import BudgetService
from app.services.goal_service import GoalService
from app.services.user_service import UserService
from app.services import plaid_service
from app.services.transaction_sync_service import transaction_sync_service
from app.services.account_sync_monitor import account_sync_monitor
from app.services.enhanced_reconciliation_service import enhanced_reconciliation_service
from app.services.automatic_sync_scheduler import automatic_sync_scheduler
from app.services.analytics_service import analytics_service
from app.services.notification_service import NotificationService
from app.services.merchant_service import merchant_service
from app.services.auto_categorization_service import AutoCategorizationService
from app.services.rule_template_service import RuleTemplateService
from app.services.financial_health_service import FinancialHealthService
from app.websocket.manager import redis_websocket_manager, get_websocket_manager


# Core service dependencies
def get_account_service() -> AccountService:
    """Dependency injection for AccountService."""
    return AccountService()


def get_transaction_service() -> TransactionService:
    """Dependency injection for TransactionService."""
    return TransactionService()


def get_category_service() -> CategoryService:
    """Dependency injection for CategoryService."""
    return CategoryService()


def get_budget_service() -> BudgetService:
    """Dependency injection for BudgetService."""
    return BudgetService()


def get_goal_service():
    """Dependency injection for GoalService with WebSocket manager."""
    return GoalService(websocket_manager=get_websocket_manager())


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency injection for UserService."""
    return UserService()


# Plaid and sync services (singletons)
def get_plaid_service():
    """Dependency injection for Plaid orchestration service."""
    return plaid_service


def get_transaction_sync_service():
    """Dependency injection for transaction sync service."""
    return transaction_sync_service


def get_account_sync_monitor():
    """Dependency injection for account sync monitor."""
    return account_sync_monitor


def get_enhanced_reconciliation_service():
    """Dependency injection for enhanced reconciliation service."""
    return enhanced_reconciliation_service


def get_automatic_sync_scheduler():
    """Dependency injection for automatic sync scheduler."""
    return automatic_sync_scheduler


def get_analytics_service():
    """Dependency injection for analytics service."""
    return analytics_service


def get_notification_service() -> NotificationService:
    """Dependency injection for NotificationService."""
    return NotificationService()


def get_merchant_service():
    """Dependency injection for merchant service (singleton)."""
    return merchant_service


def get_auto_categorization_service() -> AutoCategorizationService:
    """Dependency injection for AutoCategorizationService."""
    return AutoCategorizationService()


def get_rule_template_service() -> RuleTemplateService:
    """Dependency injection for RuleTemplateService."""
    return RuleTemplateService()


def get_financial_health_service() -> FinancialHealthService:
    """Dependency injection for FinancialHealthService."""
    return FinancialHealthService()


# WebSocket manager
def get_websocket_manager_dep():
    """Dependency injection for WebSocket manager."""
    return redis_websocket_manager


# Resource ownership dependencies
def get_owned_account(
    account_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service)
):
    """
    Dependency to fetch and validate account ownership.
    Returns the account if it exists and belongs to the current user.
    Raises 404 HTTPException if not found or not owned by user.
    """
    from fastapi import HTTPException, status
    
    account = account_service.get(db=db, id=account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return account


def get_owned_transaction(
    transaction_id,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """
    Dependency to fetch and validate transaction ownership.
    Returns the transaction if it exists and belongs to the current user.
    Raises 404 HTTPException if not found or not owned by user.
    """
    from fastapi import HTTPException, status
    
    transaction = transaction_service.get_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return transaction


def get_owned_budget(
    budget_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """
    Dependency to fetch and validate budget ownership.
    Returns the budget if it exists and belongs to the current user.
    Raises 404 HTTPException if not found or not owned by user.
    """
    from fastapi import HTTPException, status
    
    budget = budget_service.get(db=db, id=budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    return budget


def get_owned_goal(
    goal_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    goal_service = Depends(get_goal_service)
):
    """
    Dependency to fetch and validate goal ownership.
    Returns the goal if it exists and belongs to the current user.
    Raises 404 HTTPException if not found or not owned by user.
    """
    from fastapi import HTTPException, status
    
    goal = goal_service.get(db=db, id=goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    return goal