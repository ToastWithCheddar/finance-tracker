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
from .user_preferences_service import UserPreferencesService

__all__ = [
    'BaseService',
    'DataValidationService',
    'validation_service',
    'UserService',
    'CategoryService', 
    'TransactionService',
    'BudgetService',
    'GoalService',
    'UserPreferencesService',
]