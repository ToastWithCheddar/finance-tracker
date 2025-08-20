from .base import Base, BaseModel

# Import models in the correct order to avoid circular dependencies
from .user import User
from .user_session import UserSession
from .category import Category  
from .account import Account
from .transaction import Transaction
from .plaid_recurring_transaction import PlaidRecurringTransaction
from .categorization_rule import CategorizationRule
from .categorization_rule_template import CategorizationRuleTemplate
from .budget import Budget
from .budget_alert_settings import BudgetAlertSettings
from .goal import Goal
from .notification import Notification, NotificationType, NotificationPriority
from .ml_model import MLModelPerformance
from .saved_filter import SavedFilter

# Configure relationships after all models are loaded
def configure_relationships():
    """Configure model relationships after all models are imported"""
    pass

# Call configuration
configure_relationships()

__all__ = [
    "Base",
    "BaseModel", 
    "User",
    "UserSession",
    "Category",
    "Account", 
    "Transaction",
    "PlaidRecurringTransaction",
    "CategorizationRule",
    "CategorizationRuleTemplate",
    "Budget",
    "BudgetAlertSettings",
    "Goal",
    "Notification",
    "NotificationType",
    "NotificationPriority",
    "MLModelPerformance",
    "SavedFilter",
]