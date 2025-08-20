"""
Services module initialization
Handles service dependencies and prevents circular imports
"""

# Import base services that don't depend on others
from .base_service import BaseService
from .validation_service import DataValidationService, validation_service

# Import user service (base dependency for others)
from .user_service import UserService

# Import other services that depend on user service
from .category_service import CategoryService
from .transaction_service import TransactionService
from .budget_service import BudgetService
from .goal_service import GoalService

# Import Plaid services - centralized to prevent circular imports
from .plaid_client_service import PlaidClientService, plaid_client_service
from .plaid_account_service import PlaidAccountService, plaid_account_service
from .plaid_transaction_service import PlaidTransactionService, plaid_transaction_service
from .plaid_webhook_service import PlaidWebhookService, plaid_webhook_service
from .plaid_orchestration_service import PlaidOrchestrationService

# Import utilities
from .utils import plaid_utils

# Create centralized Plaid service instances to prevent circular imports
plaid_service = PlaidOrchestrationService()

__all__ = [
    'BaseService',
    'DataValidationService',
    'validation_service',
    'UserService',
    'CategoryService', 
    'TransactionService',
    'BudgetService',
    'GoalService',
    'plaid_client_service',
    'plaid_account_service',
    'plaid_transaction_service',
    'plaid_webhook_service',
    'plaid_service',
    'plaid_utils',
]