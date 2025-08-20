from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import logging

from app.database import get_db
from app.dependencies import get_user_service
from app.auth.dependencies import verify_supabase_webhook, verify_plaid_webhook
from app.services.user_service import UserService
from app.services.transaction_sync_service import transaction_sync_service
from app.services import plaid_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/supabase", status_code=200)
async def handle_supabase_webhook(
    request: Request,
    is_valid: bool = Depends(verify_supabase_webhook),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service)
):
    """Handle incoming Supabase webhook events for user management."""
    try:
        payload = await request.json()
        event_type = payload.get("type")
        record = payload.get("record")

        if not event_type or not record:
            logger.warning("Webhook received with missing type or record")
            return {"status": "ignored", "reason": "Missing type or record"}

        supabase_id = uuid.UUID(record.get("id"))
        logger.info(f"Processing webhook event: {event_type} for user: {supabase_id}")

        if event_type == "user.updated":
            user = user_service.update_user_from_webhook(db, supabase_id, record)
            if user:
                logger.info(f"Successfully updated user: {user.email}")
                return {"status": "processed", "action": "user_updated", "user_id": str(user.id)}
            else:
                logger.warning(f"Failed to update user with Supabase ID: {supabase_id}")
                return {"status": "ignored", "reason": "User not found or update failed"}

        elif event_type == "user.deleted":
            user = user_service.delete_user_by_supabase_id(db, supabase_id)
            if user:
                logger.info(f"Successfully deactivated user: {user.email}")
                return {"status": "processed", "action": "user_deleted", "user_id": str(user.id)}
            else:
                logger.warning(f"Failed to deactivate user with Supabase ID: {supabase_id}")
                return {"status": "ignored", "reason": "User not found or deactivation failed"}

        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
            return {"status": "ignored", "reason": "Event type not handled"}

    except ValueError as e:
        logger.error(f"Invalid UUID in webhook payload: {e}")
        return {"status": "error", "reason": "Invalid user ID format"}
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}")
        return {"status": "error", "reason": "Internal server error"}

@router.post("/plaid", status_code=200)
async def handle_plaid_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    is_valid: bool = Depends(verify_plaid_webhook),
    db: Session = Depends(get_db)
):
    """Handle incoming Plaid webhook events for real-time transaction updates."""
    try:
        payload = await request.json()
        webhook_type = payload.get("webhook_type")
        webhook_code = payload.get("webhook_code")
        
        logger.info(f"Received Plaid webhook: {webhook_type} - {webhook_code}")

        if webhook_type == "TRANSACTIONS":
            item_id = payload.get("item_id")
            
            if webhook_code in ("INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"):
                # Acknowledge the webhook immediately by returning 200 OK,
                # and run the actual sync in the background.
                background_tasks.add_task(
                    sync_transactions_for_item,
                    db=db,
                    item_id=item_id
                )
                logger.info(f"Scheduled background sync for Plaid item: {item_id}")
                return {"status": "sync scheduled"}
            
            elif webhook_code == "TRANSACTIONS_REMOVED":
                # Handle removed transactions in the background
                background_tasks.add_task(
                    handle_removed_transactions,
                    db=db,
                    item_id=item_id,
                    removed_transactions=payload.get("removed_transactions", [])
                )
                logger.info(f"Scheduled removal processing for Plaid item: {item_id}")
                return {"status": "removal scheduled"}

        elif webhook_type == "ITEM":
            item_id = payload.get("item_id")
            
            if webhook_code in ("ERROR", "PENDING_EXPIRATION"):
                # Handle item errors or pending expiration
                background_tasks.add_task(
                    handle_item_error,
                    db=db,
                    item_id=item_id,
                    error=payload.get("error")
                )
                logger.info(f"Scheduled item error handling for Plaid item: {item_id}")
                return {"status": "error handling scheduled"}

        elif webhook_type == "RECURRING_TRANSACTIONS":
            item_id = payload.get("item_id")
            
            if webhook_code == "RECURRING_TRANSACTIONS_UPDATE":
                # Handle recurring transactions update in the background
                background_tasks.add_task(
                    handle_recurring_transactions_update,
                    db=db,
                    item_id=item_id,
                    account_ids=payload.get("account_ids", [])
                )
                logger.info(f"Scheduled recurring transactions update for Plaid item: {item_id}")
                return {"status": "recurring transactions update scheduled"}

        return {"status": "ignored", "reason": "Webhook type not handled"}

    except Exception as e:
        logger.error(f"Unexpected error processing Plaid webhook: {e}")
        return {"status": "error", "reason": "Internal server error"}

async def sync_transactions_for_item(db: Session, item_id: str):
    """Syncs transactions for all accounts connected to a specific Plaid Item."""
    try:
        result = await transaction_sync_service.sync_transactions_for_item(
            db=db, 
            item_id=item_id, 
            days=30  # Sync last 30 days
        )
        logger.info(f"Webhook sync completed: {result}")
    except Exception as e:
        logger.error(f"Webhook-triggered sync failed: {e}")

async def handle_removed_transactions(db: Session, item_id: str, removed_transactions: list):
    """Handle transactions that were removed from Plaid."""
    from app.models.transaction import Transaction
    
    for removed_txn in removed_transactions:
        plaid_transaction_id = removed_txn.get("transaction_id")
        if plaid_transaction_id:
            # Find and mark the transaction as removed
            transaction = db.query(Transaction).filter(
                Transaction.plaid_transaction_id == plaid_transaction_id
            ).first()
            
            if transaction:
                logger.info(f"Marking transaction as removed: {plaid_transaction_id}")
                transaction.status = "removed"
                transaction.metadata_json = transaction.metadata_json or {}
                transaction.metadata_json["removed_by_webhook"] = True
                db.add(transaction)
    
    db.commit()
    logger.info(f"Processed {len(removed_transactions)} removed transactions")

async def handle_item_error(db: Session, item_id: str, error: dict):
    """Handle Plaid item errors."""
    from app.models.account import Account
    
    accounts = db.query(Account).filter(Account.plaid_item_id == item_id).all()
    for account in accounts:
        account.connection_health = "failed"
        account.last_sync_error = error.get("error_message", "Unknown error")
        db.add(account)
    
    db.commit()
    logger.info(f"Updated {len(accounts)} accounts with error status for item {item_id}")

async def handle_recurring_transactions_update(db: Session, item_id: str, account_ids: list):
    """Handle Plaid recurring transactions update webhook."""
    try:
        from app.models.account import Account
        
        logger.info(f"Processing recurring transactions update for item {item_id}, accounts: {account_ids}")
        
        # Find all accounts for this item
        query = db.query(Account).filter(Account.plaid_item_id == item_id)
        
        # If specific account IDs are provided, filter by them
        if account_ids:
            query = query.filter(Account.plaid_account_id.in_(account_ids))
        
        accounts = query.all()
        
        if not accounts:
            logger.warning(f"No accounts found for item {item_id} in recurring transactions webhook")
            return
        
        # Get the user ID from the first account (all accounts should belong to same user for an item)
        user_id = accounts[0].user_id
        
        # Use the enhanced Plaid service to sync recurring transactions
        result = await plaid_service.sync_recurring_transactions_for_user(
            db=db, 
            user_id=user_id
        )
        
        logger.info(f"Recurring transactions webhook sync completed for user {user_id}: {result}")
        
        # Send WebSocket notification about the update
        try:
            from app.websocket.manager import redis_websocket_manager as websocket_manager
            from app.websocket.events import WebSocketEvent, EventType
            
            notification_event = WebSocketEvent(
                type=EventType.NOTIFICATION,
                data={
                    "type": "recurring_transactions_updated",
                    "title": "Recurring Transactions Updated",
                    "message": f"Found {result.get('new_recurring_transactions', 0)} new and updated {result.get('updated_recurring_transactions', 0)} existing recurring transactions",
                    "timestamp": db.query(func.now()).scalar().isoformat()
                }
            )
            await websocket_manager.send_to_user(str(user_id), notification_event.to_dict())
            logger.info(f"Sent recurring transactions update notification to user {user_id}")
            
        except Exception as notification_error:
            logger.error(f"Failed to send notification for recurring transactions update: {notification_error}")
        
    except Exception as e:
        logger.error(f"Failed to process recurring transactions update webhook for item {item_id}: {e}")
        # Don't re-raise as this is a background task