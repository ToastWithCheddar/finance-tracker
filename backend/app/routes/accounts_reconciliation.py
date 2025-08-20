"""
Account reconciliation and health API endpoints.
Handles balance reconciliation, health checks, and discrepancy management.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.dependencies import (
    get_account_service,
    get_enhanced_reconciliation_service,
    get_websocket_manager_dep,
    get_financial_health_service
)
from app.models.user import User
from app.models.account import Account
from app.services.account_service import AccountService
from app.services.financial_health_service import FinancialHealthService
from app.schemas.account_health import AccountHealthResponse
from app.websocket.events import WebSocketEvent, EventType
from app.core.exceptions import (
    AccountNotFoundError,
    AuthorizationError,
    ExternalServiceError,
    ValidationError
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{account_id}/reconcile", response_model=Dict[str, Any])
async def reconcile_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service),
    reconciliation_service=Depends(get_enhanced_reconciliation_service),
    websocket_manager=Depends(get_websocket_manager_dep)
):
    """Reconcile account balance with transaction history"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account:
            raise AccountNotFoundError(account_id)
        if account.user_id != current_user.id:
            raise AuthorizationError("Not authorized to access this account")
        
        result = await reconciliation_service.reconcile_account(db, account_id)
        
        # Send real-time notification
        event = WebSocketEvent(
            event_type=EventType.ACCOUNT_RECONCILED,
            data={
                "account_id": account_id,
                "account_name": result['account_name'],
                "is_reconciled": result['is_reconciled'],
                "discrepancy": result['discrepancy'],
                "reconciliation_date": result['reconciliation_date']
            }
        )
        await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
        
        return {
            "success": True,
            "data": result
        }
        
    except (AccountNotFoundError, AuthorizationError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Failed to reconcile account {account_id}: {e}", exc_info=True)
        raise ExternalServiceError("Reconciliation Service", "Unable to reconcile account")


@router.post("/reconcile-all", response_model=Dict[str, Any])
async def reconcile_all_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    reconciliation_service=Depends(get_enhanced_reconciliation_service),
    websocket_manager=Depends(get_websocket_manager_dep)
):
    """Reconcile all user accounts"""
    try:
        result = await reconciliation_service.reconcile_all_accounts(db, str(current_user.id))
        
        # Send summary notification
        event = WebSocketEvent(
            event_type=EventType.BULK_RECONCILIATION_COMPLETE,
            data={
                "total_accounts": result['total_accounts'],
                "reconciled_accounts": result['reconciled_accounts'],
                "accounts_with_discrepancies": result['accounts_with_discrepancies'],
                "total_discrepancy": result['total_discrepancy']
            }
        )
        await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
        
        return {
            "success": True,
            "message": f"Reconciled {result['total_accounts']} accounts",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to reconcile all accounts for user {current_user.id}: {e}", exc_info=True)
        raise ExternalServiceError("Reconciliation Service", "Unable to reconcile accounts")


@router.post("/{account_id}/reconciliation-entry", response_model=Dict[str, Any])
async def create_reconciliation_entry(
    account_id: str,
    adjustment_cents: int,
    description: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service),
    reconciliation_service=Depends(get_enhanced_reconciliation_service),
    websocket_manager=Depends(get_websocket_manager_dep)
):
    """Create manual reconciliation entry to fix balance discrepancy"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account:
            raise AccountNotFoundError(account_id)
        if account.user_id != current_user.id:
            raise AuthorizationError("Not authorized to access this account")
        
        transaction = await reconciliation_service.create_reconciliation_entry(
            db, account_id, adjustment_cents, description, str(current_user.id)
        )
        
        # Send real-time notification
        event = WebSocketEvent(
            event_type=EventType.RECONCILIATION_ENTRY_CREATED,
            data={
                "account_id": account_id,
                "transaction_id": str(transaction.id),
                "adjustment_amount": adjustment_cents / 100,
                "description": description
            }
        )
        await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
        
        return {
            "success": True,
            "message": "Reconciliation entry created successfully",
            "data": {
                "transaction_id": str(transaction.id),
                "adjustment_amount": adjustment_cents / 100,
                "description": description
            }
        }
        
    except (AccountNotFoundError, AuthorizationError, ValidationError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Failed to create reconciliation entry for account {account_id}: {e}", exc_info=True)
        raise ExternalServiceError("Reconciliation Service", "Unable to create reconciliation entry")


@router.get("/{account_id}/reconciliation-history", response_model=Dict[str, Any])
async def get_reconciliation_history(
    account_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service),
    reconciliation_service=Depends(get_enhanced_reconciliation_service)
):
    """Get reconciliation history for an account"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account:
            raise AccountNotFoundError(account_id)
        if account.user_id != current_user.id:
            raise AuthorizationError("Not authorized to access this account")
        
        history = await reconciliation_service.get_reconciliation_history(db, account_id, days)
        
        return {
            "success": True,
            "data": {
                "account_id": account_id,
                "history": history,
                "period_days": days
            }
        }
        
    except (AccountNotFoundError, AuthorizationError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Failed to get reconciliation history for account {account_id}: {e}", exc_info=True)
        raise ExternalServiceError("Reconciliation Service", "Unable to retrieve reconciliation history")


@router.get("/{account_id}/health", response_model=AccountHealthResponse)
async def get_account_health(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service),
    reconciliation_service=Depends(get_enhanced_reconciliation_service),
    financial_health_service: FinancialHealthService = Depends(get_financial_health_service)
):
    """Get comprehensive account health information"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account:
            raise AccountNotFoundError(account_id)
        if account.user_id != current_user.id:
            raise AuthorizationError("Not authorized to access this account")
        
        # Get reconciliation status
        reconciliation = await reconciliation_service.reconcile_account(db, account_id)
        
        # Calculate comprehensive account health using service
        health_data = financial_health_service.calculate_account_health(
            account=account,
            reconciliation=reconciliation
        )
        
        return AccountHealthResponse(
            success=True,
            data=health_data
        )
        
    except (AccountNotFoundError, AuthorizationError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Failed to get account health for account {account_id}: {e}", exc_info=True)
        raise ExternalServiceError("Financial Health Service", "Unable to calculate account health")

