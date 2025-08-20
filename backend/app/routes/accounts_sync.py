"""
Account synchronization API endpoints.
Handles balance sync, transaction sync, scheduling, and monitoring.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.dependencies import (
    get_account_service,
    get_plaid_service,
    get_transaction_sync_service,
    get_account_sync_monitor,
    get_automatic_sync_scheduler,
    get_websocket_manager_dep,
    get_owned_account
)
from app.models.user import User
from app.models.account import Account
from app.services.account_service import AccountService
from app.websocket.events import WebSocketEvent, EventType
from app.core.exceptions import (
    ExternalServiceError,
    AccountNotFoundError,
    ValidationError,
    ConfigurationError
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sync-balances", response_model=Dict[str, Any])
async def sync_account_balances(
    account_ids: Optional[List[str]] = Body(None, embed=True),
    force_sync: bool = Body(False, embed=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service),
    plaid_service=Depends(get_plaid_service),
    websocket_manager=Depends(get_websocket_manager_dep)
):
    """Manually trigger account balance sync"""
    try:
        # Filter account_ids to user's accounts only
        if account_ids:
            user_accounts = db.query(Account).filter(
                Account.user_id == current_user.id,
                Account.id.in_(account_ids)
            ).all()
            account_ids = [str(acc.id) for acc in user_accounts]
        
        result = await plaid_service.sync_account_balances(
            db, 
            account_ids=account_ids, 
            user_id=current_user.id if not account_ids else None,
            force_sync=force_sync
        )
        
        # Send real-time notifications for each synced account
        for synced_account in result.get('synced', []):
            event = WebSocketEvent(
                event_type=EventType.ACCOUNT_BALANCE_UPDATED,
                data={
                    "account_id": synced_account['account_id'],
                    "account_name": synced_account['name'],
                    "old_balance": synced_account['old_balance'],
                    "new_balance": synced_account['new_balance'],
                    "change": synced_account['change'],
                    "sync_time": datetime.now(timezone.utc).isoformat()
                }
            )
            await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
        
        return {
            "success": True,
            "message": f"Synced {len(result['synced'])} accounts successfully",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to sync balances: {e}", exc_info=True)
        raise ExternalServiceError("Sync Service", "Unable to sync account balances")


@router.post("/sync-transactions", response_model=Dict[str, Any])
async def sync_transactions(
    account_ids: Optional[List[str]] = Body(None),
    days: int = Body(90),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    transaction_sync_service=Depends(get_transaction_sync_service)
):
    """Sync transactions for specified accounts or all user accounts"""
    try:
        if account_ids:
            # Verify account ownership
            user_accounts = db.query(Account).filter(
                Account.user_id == current_user.id,
                Account.id.in_(account_ids)
            ).all()
            
            if len(user_accounts) != len(account_ids):
                raise AccountNotFoundError("One or more accounts not found or not owned by user")
            
            # Sync specific accounts
            results = []
            for account in user_accounts:
                try:
                    result = await transaction_sync_service.sync_account_transactions(
                        str(account.id), db, days=days
                    )
                    results.append({
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "success": True,
                        "new_transactions": result.new_transactions,
                        "updated_transactions": result.updated_transactions,
                        "sync_duration": result.sync_duration_seconds
                    })
                except Exception as e:
                    results.append({
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"Synced transactions for {len(account_ids)} accounts",
                "data": {"results": results}
            }
        else:
            # Sync all user accounts
            result = await transaction_sync_service.sync_user_transactions(
                str(current_user.id), db, days=days
            )
            return {
                "success": True,
                "message": f"Synced transactions for all accounts",
                "data": result
            }
        
    except AccountNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to sync transactions: {e}", exc_info=True)
        raise ExternalServiceError("Sync Service", "Unable to sync transactions")


@router.get("/sync-overview", response_model=Dict[str, Any])
async def get_sync_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_sync_monitor=Depends(get_account_sync_monitor)
):
    """Get comprehensive sync overview for user's accounts"""
    try:
        overview = await account_sync_monitor.get_user_sync_overview(
            str(current_user.id), db
        )
        
        return {
            "success": True,
            "data": overview
        }
        
    except Exception as e:
        logger.error(f"Failed to get sync overview: {e}", exc_info=True)
        raise ExternalServiceError("Sync Service", "Unable to retrieve sync overview")


@router.get("/{account_id}/sync-status", response_model=Dict[str, Any])
async def get_account_sync_status(
    account = Depends(get_owned_account),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_sync_monitor=Depends(get_account_sync_monitor)
):
    """Get detailed sync status for a specific account"""
    try:
        
        sync_status = await account_sync_monitor.get_account_sync_status(str(account.id), db)
        
        return {
            "success": True,
            "data": {
                "account_id": sync_status.account_id,
                "account_name": sync_status.account_name,
                "account_type": sync_status.account_type,
                "is_plaid_connected": sync_status.is_plaid_connected,
                "sync_health": sync_status.sync_health.value,
                "sync_frequency": sync_status.sync_frequency.value,
                "last_sync": sync_status.last_sync.isoformat() if sync_status.last_sync else None,
                "last_successful_sync": sync_status.last_successful_sync.isoformat() if sync_status.last_successful_sync else None,
                "next_scheduled_sync": sync_status.next_scheduled_sync.isoformat() if sync_status.next_scheduled_sync else None,
                "sync_errors": sync_status.sync_errors,
                "balance_sync_status": sync_status.balance_sync_status,
                "transaction_sync_status": sync_status.transaction_sync_status,
                "connection_quality": sync_status.connection_quality,
                "sync_performance": sync_status.sync_performance,
                "recommendations": sync_status.recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get account sync status: {e}", exc_info=True)
        raise ExternalServiceError("Sync Service", "Unable to retrieve account sync status")


@router.post("/sync/schedule-automatic", response_model=Dict[str, Any])
async def schedule_automatic_sync(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    automatic_sync_scheduler=Depends(get_automatic_sync_scheduler)
):
    """Start automatic sync scheduling for user's accounts"""
    try:
        # Start the scheduler if not running
        if not automatic_sync_scheduler.is_running:
            await automatic_sync_scheduler.start_scheduler()
        
        # Get scheduler status
        status = automatic_sync_scheduler.get_scheduler_status()
        
        return {
            "success": True,
            "message": "Automatic sync scheduler is active",
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Failed to start automatic sync scheduler: {e}", exc_info=True)
        raise ConfigurationError("Unable to start automatic sync scheduler")


@router.get("/sync/scheduler-status", response_model=Dict[str, Any])
async def get_scheduler_status(
    current_user: User = Depends(get_current_active_user),
    automatic_sync_scheduler=Depends(get_automatic_sync_scheduler)
):
    """Get current scheduler status"""
    try:
        status = automatic_sync_scheduler.get_scheduler_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}", exc_info=True)
        raise ConfigurationError("Unable to retrieve scheduler status")


@router.post("/{account_id}/sync/immediate", response_model=Dict[str, Any])
async def trigger_immediate_sync(
    account = Depends(get_owned_account),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    automatic_sync_scheduler=Depends(get_automatic_sync_scheduler)
):
    """Trigger immediate sync for a specific account"""
    try:        
        result = await automatic_sync_scheduler.schedule_immediate_sync(
            str(account.id), str(current_user.id)
        )
        
        return {
            "success": result['success'],
            "message": result['message'],
            "data": result.get('result', result.get('error'))
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger immediate sync: {e}", exc_info=True)
        raise ExternalServiceError("Sync Service", "Unable to trigger immediate sync")


@router.put("/{account_id}/sync-frequency", response_model=Dict[str, Any])
async def update_sync_frequency(
    frequency: str,
    account = Depends(get_owned_account),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    automatic_sync_scheduler=Depends(get_automatic_sync_scheduler)
):
    """Update sync frequency for an account"""
    try:        
        result = await automatic_sync_scheduler.update_account_sync_frequency(
            str(account.id), frequency, db
        )
        
        return {
            "success": result['success'],
            "message": result['message']
        }
        
    except Exception as e:
        logger.error(f"Failed to update sync frequency: {e}", exc_info=True)
        raise ValidationError("Unable to update sync frequency")