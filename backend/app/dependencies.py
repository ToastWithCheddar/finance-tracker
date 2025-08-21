"""
Central dependency injection for all services across the application.
Ensures consistent service instantiation patterns and makes testing easier.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.services.account_service import get_account_service
from app.services.transaction_service import get_transaction_service
from app.services.category_service import CategoryService
from app.services.budget_service import BudgetService
from app.services.goal_service import GoalService
from app.services.user_service import UserService
from app.services.plaid_orchestration_service import get_plaid_service
from app.services.transaction_sync_service import get_transaction_sync_service
from app.services.account_sync_monitor import get_account_sync_monitor
from app.services.reconciliation_service import get_enhanced_reconciliation_service
from app.services.analytics_service import get_analytics_service
from app.services.notification_service import NotificationService
from app.services.merchant_service import get_merchant_service
from app.services.auto_categorization_service import AutoCategorizationService
from app.services.rule_template_service import RuleTemplateService
from app.services.financial_health_service import FinancialHealthService
from app.websocket.manager import redis_websocket_manager


# Core service dependencies using provider functions


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


# Additional service dependencies
def get_notification_service() -> NotificationService:
    """Dependency injection for NotificationService."""
    return NotificationService()


# Engine services (stateless singletons with lazy caching)
_auto_categorization_service_instance = None

def get_auto_categorization_service() -> AutoCategorizationService:
    """Dependency injection for AutoCategorizationService."""
    global _auto_categorization_service_instance
    if _auto_categorization_service_instance is None:
        _auto_categorization_service_instance = AutoCategorizationService()
    return _auto_categorization_service_instance


_rule_template_service_instance = None

def get_rule_template_service() -> RuleTemplateService:
    """Dependency injection for RuleTemplateService."""
    global _rule_template_service_instance
    if _rule_template_service_instance is None:
        _rule_template_service_instance = RuleTemplateService()
    return _rule_template_service_instance


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
    account_service = Depends(get_account_service)
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
    transaction_service = Depends(get_transaction_service)
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
    budget_service = Depends(get_budget_service)
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