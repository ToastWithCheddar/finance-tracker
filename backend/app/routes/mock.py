"""
Mock API routes for UI development without database
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Any, Dict, List
import logging

from app.config import settings
from app.services.mock_data_service import mock_data_service

logger = logging.getLogger(__name__)

router = APIRouter()

def check_mock_mode():
    """Check if mock mode is enabled"""
    if not settings.USE_MOCK_DATA and not settings.UI_ONLY_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock endpoints are disabled. Set USE_MOCK_DATA=true or UI_ONLY_MODE=true to enable."
        )

@router.get("/health")
async def mock_health():
    """Mock health check endpoint"""
    check_mock_mode()
    return {
        "status": "ok",
        "mode": "mock",
        "message": "Mock API is running for UI development"
    }

@router.get("/me")
async def mock_get_me():
    """Mock current user endpoint"""
    check_mock_mode()
    return mock_data_service.get_mock_user()

@router.post("/login")
async def mock_login(login_data: Dict[str, Any]):
    """Mock login endpoint"""
    check_mock_mode()
    return {
        "access_token": "mock-access-token-12345",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": mock_data_service.get_mock_user(),
        "message": "Mock login successful"
    }

@router.post("/register")
async def mock_register(user_data: Dict[str, Any]):
    """Mock registration endpoint"""
    check_mock_mode()
    return {
        "access_token": "mock-access-token-12345",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": mock_data_service.get_mock_user(),
        "message": "Mock registration successful"
    }

@router.get("/accounts")
async def mock_get_accounts():
    """Mock accounts endpoint"""
    check_mock_mode()
    return mock_data_service.get_mock_accounts()

@router.get("/transactions")
async def mock_get_transactions(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """Mock transactions endpoint"""
    check_mock_mode()
    transactions = mock_data_service.get_mock_transactions(limit=limit + skip)
    return transactions[skip:skip + limit]

@router.get("/categories")
async def mock_get_categories():
    """Mock categories endpoint"""
    check_mock_mode()
    return mock_data_service.get_mock_categories()

@router.get("/budgets")
async def mock_get_budgets():
    """Mock budgets endpoint"""
    check_mock_mode()
    return mock_data_service.get_mock_budgets()

@router.get("/goals")
async def mock_get_goals():
    """Mock goals endpoint"""
    check_mock_mode()
    return mock_data_service.get_mock_goals()

@router.get("/dashboard/summary")
async def mock_dashboard_summary():
    """Mock dashboard summary endpoint"""
    check_mock_mode()
    return mock_data_service.get_dashboard_summary()

# Mock POST endpoints for UI testing
@router.post("/accounts")
async def mock_create_account(account_data: Dict[str, Any]):
    """Mock create account endpoint"""
    check_mock_mode()
    return {
        "id": "mock-account-new",
        "message": "Mock account created successfully",
        **account_data
    }

@router.post("/transactions")
async def mock_create_transaction(transaction_data: Dict[str, Any]):
    """Mock create transaction endpoint"""
    check_mock_mode()
    return {
        "id": "mock-transaction-new",
        "message": "Mock transaction created successfully",
        **transaction_data
    }

@router.post("/categories")
async def mock_create_category(category_data: Dict[str, Any]):
    """Mock create category endpoint"""
    check_mock_mode()
    return {
        "id": "mock-category-new",
        "message": "Mock category created successfully",
        **category_data
    }

@router.post("/budgets")
async def mock_create_budget(budget_data: Dict[str, Any]):
    """Mock create budget endpoint"""
    check_mock_mode()
    return {
        "id": "mock-budget-new",
        "message": "Mock budget created successfully",
        **budget_data
    }

@router.post("/goals")
async def mock_create_goal(goal_data: Dict[str, Any]):
    """Mock create goal endpoint"""
    check_mock_mode()
    return {
        "id": "mock-goal-new",
        "message": "Mock goal created successfully",
        **goal_data
    }

# Mock PUT endpoints for UI testing
@router.put("/accounts/{account_id}")
async def mock_update_account(account_id: str, account_data: Dict[str, Any]):
    """Mock update account endpoint"""
    check_mock_mode()
    return {
        "id": account_id,
        "message": "Mock account updated successfully",
        **account_data
    }

@router.put("/transactions/{transaction_id}")
async def mock_update_transaction(transaction_id: str, transaction_data: Dict[str, Any]):
    """Mock update transaction endpoint"""
    check_mock_mode()
    return {
        "id": transaction_id,
        "message": "Mock transaction updated successfully",
        **transaction_data
    }

# Mock DELETE endpoints for UI testing
@router.delete("/accounts/{account_id}")
async def mock_delete_account(account_id: str):
    """Mock delete account endpoint"""
    check_mock_mode()
    return {
        "message": f"Mock account {account_id} deleted successfully"
    }

@router.delete("/transactions/{transaction_id}")
async def mock_delete_transaction(transaction_id: str):
    """Mock delete transaction endpoint"""
    check_mock_mode()
    return {
        "message": f"Mock transaction {transaction_id} deleted successfully"
    }

# Mock Plaid endpoints
@router.post("/plaid/link_token")
async def mock_plaid_link_token(user_data: Dict[str, Any]):
    """Mock Plaid link token endpoint"""
    check_mock_mode()
    return {
        "link_token": "link-development-12345",
        "expiration": "2024-01-01T00:00:00Z",
        "request_id": "mock-request-id",
        "message": "Mock Plaid link token created"
    }

@router.post("/plaid/exchange_token")
async def mock_plaid_exchange_token(token_data: Dict[str, Any]):
    """Mock Plaid token exchange endpoint"""
    check_mock_mode()
    return {
        "access_token": "access-development-12345",
        "item_id": "mock-item-id",
        "accounts": mock_data_service.get_mock_accounts()[:2],  # Return 2 accounts
        "message": "Mock Plaid token exchange successful"
    }

@router.get("/plaid/accounts/{account_id}/sync")
async def mock_plaid_sync_account(account_id: str):
    """Mock Plaid account sync endpoint"""
    check_mock_mode()
    return {
        "account_id": account_id,
        "synced": True,
        "new_transactions": 5,
        "updated_balance": 2450.75,
        "message": "Mock account sync successful"
    }

# Status endpoint to show current mode
@router.get("/status")
async def mock_status():
    """Show mock API status"""
    return {
        "mock_mode_enabled": settings.USE_MOCK_DATA or settings.UI_ONLY_MODE,
        "use_mock_data": settings.USE_MOCK_DATA,
        "ui_only_mode": settings.UI_ONLY_MODE,
        "enable_database": settings.ENABLE_DATABASE,
        "enable_plaid": settings.ENABLE_PLAID,
        "message": "Mock API status information"
    }