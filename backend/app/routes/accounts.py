"""
Enhanced account management API endpoints with Plaid integration
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.models.account import Account
from app.schemas.account import (
    Account as AccountSchema, 
    AccountCreate, 
    AccountUpdate,
    AccountWithTransactions
)
from app.services.account_service import AccountService
from app.services.enhanced_plaid_service import enhanced_plaid_service
from app.services.transaction_sync_service import transaction_sync_service
from app.services.account_sync_monitor import account_sync_monitor
from app.services.enhanced_reconciliation_service import enhanced_reconciliation_service
from app.services.automatic_sync_scheduler import automatic_sync_scheduler
from app.websocket.manager import websocket_manager
from app.websocket.events import WebSocketEvent, EventType

router = APIRouter()
account_service = AccountService()

@router.get("/", response_model=List[AccountSchema])
async def get_user_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all accounts for the current user"""
    try:
        accounts = account_service.get_by_user(db=db, user_id=current_user.id)
        return accounts
    except Exception as e:
        logger.error(f"Failed to get accounts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve accounts"
        )

@router.post("/plaid/link-token", response_model=Dict[str, Any])
async def create_plaid_link_token(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create Plaid Link token for account connection"""
    try:
        result = await enhanced_plaid_service.create_link_token(str(current_user.id))
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create link token: {str(e)}"
        )

@router.post("/plaid/exchange-token", response_model=Dict[str, Any])
async def exchange_plaid_token(
    public_token: str,  # Query parameter
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Exchange Plaid public token for access token and create accounts"""
    try:
        # Debug logging to identify the issue
        logger.info(f"Exchange token request - User ID: {current_user.id if current_user else 'None'}")
        logger.info(f"Exchange token request - Public token: {public_token[:20]}..." if public_token else "No public token")
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. User not found in request context."
            )
        
        result = await enhanced_plaid_service.exchange_public_token(
            public_token, str(current_user.id), db
        )
        
        # Check if the service returned an error
        if not result.get('success', True):
            error_message = result.get('message', 'Failed to connect bank account')
            logger.error(f"Plaid service error for user {current_user.id}: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Ensure we have accounts in the result
        accounts = result.get('accounts', [])
        if not accounts:
            logger.warning(f"No accounts created for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No accounts were connected. Please try again."
            )
        
        # Send real-time notification
        try:
            event = WebSocketEvent(
                event_type=EventType.ACCOUNT_CONNECTED,
                data={
                    "message": f"Successfully connected {len(accounts)} accounts",
                    "accounts": [
                        {
                            "id": str(acc.id),
                            "name": acc.name,
                            "type": acc.account_type,
                            "balance": acc.balance_cents / 100
                        } for acc in accounts
                    ],
                    "institution": result.get('institution', {}).get('name', 'Bank')
                }
            )
            await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
            logger.info(f"Sent WebSocket notification for {len(accounts)} accounts")
        except Exception as ws_error:
            logger.warning(f"Failed to send WebSocket notification: {ws_error}")
            # Don't fail the whole process if WebSocket fails
        
        # Schedule initial sync
        try:
            background_tasks.add_task(
                _schedule_account_sync, 
                [str(acc.id) for acc in accounts], 
                db
            )
            logger.info(f"Scheduled background sync for {len(accounts)} accounts")
        except Exception as sync_error:
            logger.warning(f"Failed to schedule background sync: {sync_error}")
            # Don't fail the whole process if background task scheduling fails
        
        return {
            "success": True,
            "message": f"Successfully connected {len(accounts)} accounts",
            "data": {
                "accounts_created": len(accounts),
                "institution": result.get('institution', {}).get('name'),
                "accounts": [
                    {
                        "id": str(acc.id),
                        "name": acc.name,
                        "type": acc.account_type,
                        "balance": acc.balance_cents / 100,
                        "currency": acc.currency
                    } for acc in accounts
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange token: {str(e)}"
        )

@router.post("/sync-balances", response_model=Dict[str, Any])
async def sync_account_balances(
    account_ids: Optional[List[str]] = Body(None, embed=True),
    force_sync: bool = Body(False, embed=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
        
        result = await enhanced_plaid_service.sync_account_balances(
            db, 
            account_ids=account_ids, 
            user_id=str(current_user.id) if not account_ids else None,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync balances: {str(e)}"
        )

@router.get("/connection-status", response_model=Dict[str, Any])
async def get_connection_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get Plaid connection status for user's accounts"""
    try:
        status_info = await enhanced_plaid_service.get_connection_status(db, str(current_user.id))
        return {
            "success": True,
            "data": status_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection status: {str(e)}"
        )

@router.post("/{account_id}/reconcile", response_model=Dict[str, Any])
async def reconcile_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reconcile account balance with transaction history"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        result = await enhanced_reconciliation_service.reconcile_account(db, account_id)
        
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
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconcile account: {str(e)}"
        )

@router.post("/reconcile-all", response_model=Dict[str, Any])
async def reconcile_all_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reconcile all user accounts"""
    try:
        result = await enhanced_reconciliation_service.reconcile_all_accounts(db, str(current_user.id))
        
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconcile accounts: {str(e)}"
        )

@router.post("/{account_id}/reconciliation-entry", response_model=Dict[str, Any])
async def create_reconciliation_entry(
    account_id: str,
    adjustment_cents: int,
    description: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create manual reconciliation entry to fix balance discrepancy"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        transaction = await enhanced_reconciliation_service.create_reconciliation_entry(
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
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reconciliation entry: {str(e)}"
        )

@router.get("/{account_id}/reconciliation-history", response_model=Dict[str, Any])
async def get_reconciliation_history(
    account_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get reconciliation history for an account"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        history = await enhanced_reconciliation_service.get_reconciliation_history(db, account_id, days)
        
        return {
            "success": True,
            "data": {
                "account_id": account_id,
                "history": history,
                "period_days": days
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reconciliation history: {str(e)}"
        )

@router.get("/{account_id}/health", response_model=Dict[str, Any])
async def get_account_health(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive account health information"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # Get reconciliation status
        reconciliation = await enhanced_reconciliation_service.reconcile_account(db, account_id)
        
        # Get connection status if Plaid account
        connection_health = "not_connected"
        last_sync = None
        sync_frequency = None
        
        if account.plaid_access_token:
            metadata = account.account_metadata or {}
            last_sync = metadata.get('last_sync')
            
            if last_sync:
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', ''))
                hours_since_sync = (datetime.now(timezone.utc) - last_sync_dt).total_seconds() / 3600
                
                if hours_since_sync < 24:
                    connection_health = "healthy"
                    sync_frequency = "daily"
                elif hours_since_sync < 168:  # 1 week
                    connection_health = "warning"
                    sync_frequency = "weekly"
                else:
                    connection_health = "failed"
                    sync_frequency = "stale"
        
        health_data = {
            "account_id": account_id,
            "account_name": account.name,
            "account_type": account.account_type,
            "is_active": account.is_active,
            "current_balance": account.balance_cents / 100,
            "currency": account.currency,
            
            # Reconciliation health
            "reconciliation": {
                "is_reconciled": reconciliation['is_reconciled'],
                "discrepancy": reconciliation['discrepancy'],
                "last_reconciliation": reconciliation['reconciliation_date'],
                "transaction_count": reconciliation['transaction_count']
            },
            
            # Connection health
            "connection": {
                "health_status": connection_health,
                "is_plaid_connected": bool(account.plaid_access_token),
                "last_sync": last_sync,
                "sync_frequency": sync_frequency
            },
            
            # Overall health score (0-100)
            "health_score": _calculate_health_score(reconciliation, connection_health),
            
            # Recommendations
            "recommendations": _generate_health_recommendations(
                reconciliation, connection_health, account
            )
        }
        
        return {
            "success": True,
            "data": health_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account health: {str(e)}"
        )

async def _schedule_account_sync(account_ids: List[str], db: Session):
    """Background task to schedule account sync"""
    try:
        await enhanced_plaid_service.sync_account_balances(db, account_ids)
    except Exception as e:
        logging.getLogger(__name__).error(f"Background sync failed: {e}")

def _calculate_health_score(reconciliation: Dict[str, Any], connection_health: str) -> int:
    """Calculate overall account health score (0-100)"""
    score = 100
    
    # Reconciliation score (50% weight)
    if not reconciliation['is_reconciled']:
        discrepancy = abs(reconciliation['discrepancy'])
        if discrepancy > 100:  # $100+ discrepancy
            score -= 40
        elif discrepancy > 10:  # $10+ discrepancy
            score -= 25
        else:  # Small discrepancy
            score -= 10
    
    # Connection score (50% weight)
    if connection_health == "failed":
        score -= 40
    elif connection_health == "warning":
        score -= 20
    elif connection_health == "not_connected":
        score -= 10  # Not necessarily bad for manual accounts
    
    return max(0, score)

def _generate_health_recommendations(
    reconciliation: Dict[str, Any], 
    connection_health: str, 
    account: Account
) -> List[str]:
    """Generate health improvement recommendations"""
    recommendations = []
    
    if not reconciliation['is_reconciled']:
        recommendations.append("Reconcile account balance to resolve discrepancies")
        recommendations.extend(reconciliation.get('suggestions', [])[:3])  # Top 3 suggestions
    
    if connection_health == "failed":
        recommendations.append("Reconnect your bank account for automatic updates")
    elif connection_health == "warning":
        recommendations.append("Account sync is overdue - check your bank connection")
    
    if account.plaid_access_token and connection_health == "healthy":
        recommendations.append("Account is healthy and syncing properly")
    
    if not recommendations:
        recommendations.append("Account is in good health - no action needed")
    
    return recommendations

@router.post("/sync/schedule-automatic", response_model=Dict[str, Any])
async def schedule_automatic_sync(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start automatic sync scheduler: {str(e)}"
        )

@router.get("/sync/scheduler-status", response_model=Dict[str, Any])
async def get_scheduler_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get current scheduler status"""
    try:
        status = automatic_sync_scheduler.get_scheduler_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )

@router.post("/{account_id}/sync/immediate", response_model=Dict[str, Any])
async def trigger_immediate_sync(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Trigger immediate sync for a specific account"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        result = await automatic_sync_scheduler.schedule_immediate_sync(
            account_id, str(current_user.id)
        )
        
        return {
            "success": result['success'],
            "message": result['message'],
            "data": result.get('result', result.get('error'))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger immediate sync: {str(e)}"
        )

@router.put("/{account_id}/sync-frequency", response_model=Dict[str, Any])
async def update_sync_frequency(
    account_id: str,
    frequency: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update sync frequency for an account"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        result = await automatic_sync_scheduler.update_account_sync_frequency(
            account_id, frequency, db
        )
        
        return {
            "success": result['success'],
            "message": result['message']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sync frequency: {str(e)}"
        )

@router.get("/sync-overview", response_model=Dict[str, Any])
async def get_sync_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync overview: {str(e)}"
        )

@router.get("/{account_id}/sync-status", response_model=Dict[str, Any])
async def get_account_sync_status(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed sync status for a specific account"""
    try:
        # Verify account ownership
        account = account_service.get(db=db, id=account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        sync_status = await account_sync_monitor.get_account_sync_status(account_id, db)
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account sync status: {str(e)}"
        )

@router.post("/sync-transactions", response_model=Dict[str, Any])
async def sync_transactions(
    account_ids: Optional[List[str]] = Body(None),
    days: int = Body(90),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="One or more accounts not found or not owned by user"
                )
            
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync transactions: {str(e)}"
        )