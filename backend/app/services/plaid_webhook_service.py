"""
Plaid Webhook Service
Handles webhook processing, recurring transactions, and real-time sync events from Plaid
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.account import Account
from app.models.plaid_recurring_transaction import PlaidRecurringTransaction
from app.services.plaid_client_service import plaid_client_service
from app.services.plaid_transaction_service import plaid_transaction_service
from app.services.utils.plaid_utils import group_accounts_by_token
from app.websocket.manager import redis_websocket_manager as websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)


class PlaidWebhookService:
    """Service for handling Plaid webhooks and recurring transactions"""
    
    def __init__(self):
        pass
    
    async def sync_recurring_transactions_for_user(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Sync all recurring transactions for a user's accounts"""
        
        # Lightweight type assertion for internal bug detection
        if not isinstance(user_id, UUID):
            raise TypeError(f"user_id must be UUID, got {type(user_id)}")
        
        try:
            # Get user's Plaid-connected accounts
            user_accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.plaid_access_token_encrypted.isnot(None)
            ).all()
            
            if not user_accounts:
                return {"success": True, "message": "No Plaid accounts to sync.", "results": []}
            
            # Group accounts by access token
            token_groups = group_accounts_by_token(user_accounts)
            
            overall_results = {
                "success": True,
                "accounts_processed": len(user_accounts),
                "total_recurring_transactions": 0,
                "new_recurring_transactions": 0,
                "updated_recurring_transactions": 0,
                "total_errors": 0,
                "results": []
            }
            
            for access_token, accounts_in_group in token_groups.items():
                try:
                    # Fetch recurring transactions for this token group
                    recurring_data = await plaid_client_service.fetch_recurring_transactions(access_token)
                    
                    if not recurring_data.get('success'):
                        raise Exception(recurring_data.get('error', 'Failed to fetch recurring transactions'))
                    
                    # Process both inflow and outflow streams
                    all_streams = recurring_data.get('inflow_streams', []) + recurring_data.get('outflow_streams', [])
                    overall_results["total_recurring_transactions"] += len(all_streams)
                    
                    # Create account mapping
                    account_map = {acc.plaid_account_id: acc for acc in accounts_in_group}
                    
                    for stream in all_streams:
                        try:
                            account_id = stream.get('account_id')
                            account = account_map.get(account_id)
                            
                            if not account:
                                continue
                            
                            # Process the recurring transaction
                            processed = await self._process_plaid_recurring_transaction(stream, account, db)
                            if processed.get('created'):
                                overall_results["new_recurring_transactions"] += 1
                            elif processed.get('updated'):
                                overall_results["updated_recurring_transactions"] += 1
                                
                        except Exception as e:
                            logger.error(f"Failed to process recurring transaction {stream.get('stream_id', 'unknown')}: {e}")
                            overall_results["total_errors"] += 1
                    
                    # Add success for accounts in this group
                    for account in accounts_in_group:
                        overall_results["results"].append({
                            "account_id": str(account.id),
                            "account_name": account.name,
                            "success": True,
                            "recurring_transactions_found": len([s for s in all_streams if s.get('account_id') == account.plaid_account_id])
                        })
                
                except Exception as e:
                    logger.error(f"Failed to sync recurring transactions for token group: {e}")
                    overall_results["total_errors"] += len(accounts_in_group)
                    
                    # Add failure for accounts in this group
                    for account in accounts_in_group:
                        overall_results["results"].append({
                            "account_id": str(account.id),
                            "account_name": account.name,
                            "success": False,
                            "error": str(e)
                        })
                
                # Small delay between token groups
                await asyncio.sleep(1)
            
            db.commit()
            
            # Send WebSocket notification
            try:
                completion_event = WebSocketEvent(
                    type=EventType.DASHBOARD_UPDATE,
                    data={
                        "event": "recurring_sync_completed",
                        "details": overall_results
                    }
                )
                await websocket_manager.send_to_user(str(user_id), completion_event.to_dict())
                logger.info(f"Sent recurring transactions sync completion event to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send sync completion event to user {user_id}: {e}")
            
            return overall_results
            
        except Exception as e:
            logger.error(f"Failed to sync recurring transactions for user {user_id}: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to sync recurring transactions"
            }
    
    async def _process_plaid_recurring_transaction(
        self, 
        plaid_recurring: Dict[str, Any], 
        account: Account, 
        db: Session
    ) -> Dict[str, Any]:
        """Process individual Plaid recurring transaction"""
        try:
            stream_id = plaid_recurring.get('stream_id')
            
            # Check if we already have this recurring transaction
            existing = db.query(PlaidRecurringTransaction).filter(
                PlaidRecurringTransaction.plaid_recurring_transaction_id == stream_id
            ).first()
            
            # Extract data from Plaid stream
            description = plaid_recurring.get('description', 'Unknown Recurring Transaction')
            merchant_name = plaid_recurring.get('merchant_name')
            
            # Handle amount - Plaid recurring uses average_amount
            average_amount = plaid_recurring.get('average_amount', {})
            amount_cents = int(abs(average_amount.get('amount', 0)) * 100)
            currency = average_amount.get('iso_currency_code', 'USD')
            
            # Extract frequency and status
            frequency = plaid_recurring.get('frequency', 'UNKNOWN')
            status = plaid_recurring.get('status', 'UNKNOWN')
            
            # Get last amount and date if available
            last_amount_cents = None
            last_date = None
            if plaid_recurring.get('last_amount'):
                last_amount_cents = int(abs(plaid_recurring['last_amount'].get('amount', 0)) * 100)
            if plaid_recurring.get('last_date'):
                try:
                    last_date = datetime.fromisoformat(plaid_recurring['last_date']).date()
                except (ValueError, TypeError):
                    last_date = None
            
            # Extract categories
            personal_finance_category = plaid_recurring.get('personal_finance_category')
            categories = []
            if personal_finance_category:
                primary = personal_finance_category.get('primary')
                detailed = personal_finance_category.get('detailed')
                if primary:
                    categories.append(primary)
                if detailed and detailed != primary:
                    categories.append(detailed)
            
            current_time = datetime.now(timezone.utc)
            
            if existing:
                # Update existing record
                existing.description = description
                existing.merchant_name = merchant_name
                existing.amount_cents = amount_cents
                existing.currency = currency
                existing.frequency = frequency
                existing.status = status
                existing.last_amount_cents = last_amount_cents
                existing.last_date = last_date
                existing.plaid_categories = categories
                existing.updated_at = current_time
                
                # Update metadata
                metadata = existing.metadata or {}
                metadata.update({
                    'personal_finance_category': personal_finance_category,
                    'last_sync': current_time.isoformat(),
                    'is_active': status.upper() in ['ACTIVE', 'MATURE']
                })
                existing.metadata = metadata
                
                db.add(existing)
                logger.info(f"Updated recurring transaction: {description} for account {account.name}")
                
                return {"updated": True, "recurring_transaction": existing}
            
            else:
                # Create new recurring transaction
                recurring_txn = PlaidRecurringTransaction(
                    user_id=account.user_id,
                    account_id=account.id,
                    plaid_recurring_transaction_id=stream_id,
                    description=description,
                    merchant_name=merchant_name,
                    amount_cents=amount_cents,
                    currency=currency,
                    frequency=frequency,
                    status=status,
                    last_amount_cents=last_amount_cents,
                    last_date=last_date,
                    plaid_categories=categories,
                    metadata={
                        'personal_finance_category': personal_finance_category,
                        'first_sync': current_time.isoformat(),
                        'is_active': status.upper() in ['ACTIVE', 'MATURE']
                    },
                    is_active=status.upper() in ['ACTIVE', 'MATURE'],
                    created_at=current_time,
                    updated_at=current_time
                )
                
                db.add(recurring_txn)
                logger.info(f"Created new recurring transaction: {description} for account {account.name}")
                
                return {"created": True, "recurring_transaction": recurring_txn}
                
        except Exception as e:
            logger.error(f"Failed to process recurring transaction {plaid_recurring.get('stream_id', 'unknown')}: {e}")
            return {"error": str(e)}
    
    async def handle_webhook(self, webhook_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Handle incoming Plaid webhook"""
        try:
            webhook_type = webhook_data.get('webhook_type')
            webhook_code = webhook_data.get('webhook_code')
            item_id = webhook_data.get('item_id')
            
            logger.info(f"Processing Plaid webhook: {webhook_type}.{webhook_code} for item {item_id}")
            
            if webhook_type == 'TRANSACTIONS':
                return await self._handle_transactions_webhook(webhook_data, db)
            elif webhook_type == 'ITEM':
                return await self._handle_item_webhook(webhook_data, db)
            elif webhook_type == 'ACCOUNTS':
                return await self._handle_accounts_webhook(webhook_data, db)
            else:
                logger.warning(f"Unhandled webhook type: {webhook_type}")
                return {"success": True, "message": f"Webhook {webhook_type} acknowledged but not processed"}
        
        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_transactions_webhook(self, webhook_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Handle TRANSACTIONS webhook events"""
        webhook_code = webhook_data.get('webhook_code')
        item_id = webhook_data.get('item_id')
        
        # Find accounts for this item
        accounts = db.query(Account).filter(Account.plaid_item_id == item_id).all()
        
        if not accounts:
            logger.warning(f"No accounts found for item_id: {item_id}")
            return {"success": True, "message": "No accounts found for webhook"}
        
        if webhook_code in ['INITIAL_UPDATE', 'HISTORICAL_UPDATE', 'DEFAULT_UPDATE']:
            # Trigger transaction sync for affected accounts
            user_id = str(accounts[0].user_id)
            
            try:
                sync_result = await plaid_transaction_service.sync_transactions_for_user(db, user_id)
                logger.info(f"Webhook triggered transaction sync for user {user_id}: {sync_result.get('total_new_transactions', 0)} new transactions")
                
                return {"success": True, "sync_result": sync_result}
            
            except Exception as e:
                logger.error(f"Failed to sync transactions from webhook: {e}")
                return {"success": False, "error": str(e)}
        
        return {"success": True, "message": f"Transactions webhook {webhook_code} acknowledged"}
    
    async def _handle_item_webhook(self, webhook_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Handle ITEM webhook events"""
        webhook_code = webhook_data.get('webhook_code')
        item_id = webhook_data.get('item_id')
        error = webhook_data.get('error')
        
        # Find accounts for this item
        accounts = db.query(Account).filter(Account.plaid_item_id == item_id).all()
        
        if webhook_code == 'ERROR':
            # Update account health status
            for account in accounts:
                account.connection_health = 'error'
                account.sync_status = 'error'
                if error:
                    metadata = account.account_metadata or {}
                    metadata['last_error'] = {
                        'error_type': error.get('error_type'),
                        'error_code': error.get('error_code'),
                        'error_message': error.get('error_message'),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    account.account_metadata = metadata
                db.add(account)
            
            db.commit()
            logger.warning(f"Item error webhook for {item_id}: {error}")
        
        elif webhook_code == 'PENDING_EXPIRATION':
            # Notify user that re-authentication is needed
            if accounts:
                user_id = str(accounts[0].user_id)
                try:
                    event = WebSocketEvent(
                        type=EventType.ACCOUNT_RECONNECTION_REQUIRED,
                        data={
                            "item_id": item_id,
                            "accounts": [{"id": str(acc.id), "name": acc.name} for acc in accounts],
                            "message": "Bank connection requires re-authentication"
                        }
                    )
                    await websocket_manager.send_to_user(user_id, event.to_dict())
                except Exception as e:
                    logger.error(f"Failed to send reconnection notification: {e}")
        
        return {"success": True, "message": f"Item webhook {webhook_code} processed"}
    
    async def _handle_accounts_webhook(self, webhook_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Handle ACCOUNTS webhook events"""
        webhook_code = webhook_data.get('webhook_code')
        item_id = webhook_data.get('item_id')
        
        if webhook_code == 'DEFAULT_UPDATE':
            # Account balances have been updated, trigger balance sync
            accounts = db.query(Account).filter(Account.plaid_item_id == item_id).all()
            
            if accounts and accounts[0].plaid_access_token:
                from app.services.plaid_account_service import plaid_account_service
                try:
                    sync_result = await plaid_account_service.sync_account_balances(
                        db=db,
                        account_ids=[str(acc.id) for acc in accounts]
                    )
                    logger.info(f"Webhook triggered balance sync: {len(sync_result.get('synced', []))} accounts updated")
                    
                    return {"success": True, "sync_result": sync_result}
                
                except Exception as e:
                    logger.error(f"Failed to sync balances from webhook: {e}")
                    return {"success": False, "error": str(e)}
        
        return {"success": True, "message": f"Accounts webhook {webhook_code} acknowledged"}
    


# Create singleton instance
plaid_webhook_service = PlaidWebhookService()