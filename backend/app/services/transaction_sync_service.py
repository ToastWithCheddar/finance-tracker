"""
Transaction Synchronization Service
Handles automated transaction import and sync with Plaid
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from dataclasses import dataclass
import asyncio
from collections import defaultdict

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate
from app.services.enhanced_plaid_service import enhanced_plaid_service
from app.services.transaction_service import TransactionService
from app.websocket.manager import redis_websocket_manager as websocket_manager
from app.websocket.events import WebSocketEvent, EventType
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

@dataclass
class SyncResult:
    """Result of transaction synchronization"""
    account_id: str
    new_transactions: int
    updated_transactions: int
    duplicates_skipped: int
    errors: List[str]
    sync_duration_seconds: float
    date_range: str

class TransactionSyncService:
    """Service for synchronizing transactions with Plaid"""
    
    def __init__(self):
        self.transaction_service = TransactionService()
        self.plaid_service = enhanced_plaid_service
        
        # Sync configuration
        self.max_sync_days = 365  # Maximum days to sync in one operation
        self.default_sync_days = 30  # Default sync period for new accounts
        self.batch_size = 100  # Process transactions in batches
        
        # Lock configuration
        self.lock_timeout_seconds = 300  # 5 minutes timeout for distributed locks
    
    async def _acquire_sync_lock(self, account_id: str) -> bool:
        """
        Acquire a distributed lock for account synchronization using Redis.
        
        Args:
            account_id: The account ID to lock
            
        Returns:
            bool: True if lock was acquired, False otherwise
            
        Raises:
            Exception: If Redis connection fails
        """
        try:
            conn = await redis_client.get_connection()
            lock_key = f"sync-lock:{account_id}"
            lock_value = f"worker-{asyncio.current_task().get_name() if asyncio.current_task() else 'unknown'}"
            
            # Use SET with NX (not exists) and EX (expiration) options
            # This is atomic - either sets the key with expiration or fails
            result = await conn.set(
                lock_key, 
                lock_value, 
                nx=True,  # Only set if key doesn't exist
                ex=self.lock_timeout_seconds  # Set expiration
            )
            
            await conn.close()
            
            if result:
                logger.info(f"Acquired sync lock for account {account_id}")
                return True
            else:
                logger.warning(f"Failed to acquire sync lock for account {account_id} - already locked")
                return False
                
        except Exception as e:
            logger.error(f"Error acquiring sync lock for account {account_id}: {str(e)}")
            raise Exception(f"Failed to acquire distributed lock: {str(e)}")
    
    async def _release_sync_lock(self, account_id: str) -> bool:
        """
        Release the distributed lock for account synchronization.
        
        Args:
            account_id: The account ID to unlock
            
        Returns:
            bool: True if lock was released, False if lock didn't exist
        """
        try:
            conn = await redis_client.get_connection()
            lock_key = f"sync-lock:{account_id}"
            
            # Delete the lock key
            result = await conn.delete(lock_key)
            await conn.close()
            
            if result:
                logger.info(f"Released sync lock for account {account_id}")
                return True
            else:
                logger.warning(f"Attempted to release non-existent lock for account {account_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error releasing sync lock for account {account_id}: {str(e)}")
            # Don't raise here - we want to ensure cleanup continues
            return False
    
    async def sync_account_transactions(
        self, 
        account_id: str, 
        db: Session,
        days: int = None,
        force_sync: bool = False
    ) -> SyncResult:
        """Sync transactions for a single account"""
        
        # Attempt to acquire distributed lock
        lock_acquired = await self._acquire_sync_lock(account_id)
        if not lock_acquired:
            raise Exception(f"Account {account_id} is already being synced")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise Exception(f"Account {account_id} not found")
            
            if not account.is_plaid_connected:
                raise Exception(f"Account {account.name} is not connected to Plaid")
            
            # Determine sync date range
            sync_days = days or self._calculate_sync_days(account, force_sync)
            start_date = datetime.now(timezone.utc) - timedelta(days=sync_days)
            end_date = datetime.now(timezone.utc)
            
            logger.info(f"🔍 DEBUG: Account {account.name} sync details:")
            logger.info(f"   - Account ID: {account_id}")
            logger.info(f"   - Sync days: {sync_days}")
            logger.info(f"   - Date range: {start_date.date()} to {end_date.date()}")
            logger.info(f"   - Plaid account ID: {account.plaid_account_id}")
            
            # Update account sync status
            account.sync_status = 'syncing'
            db.add(account)
            db.commit()
            
            # Fetch transactions from Plaid
            logger.info(f"📡 DEBUG: Fetching transactions from Plaid API...")
            transactions_data = await self.plaid_service.fetch_transactions(
                account.plaid_access_token,
                start_date,
                end_date,
                [account.plaid_account_id]
            )
            
            # Debug: Log what Plaid returned
            plaid_transactions = transactions_data.get('transactions', [])
            logger.info(f"📦 DEBUG: Plaid API returned {len(plaid_transactions)} transactions")
            if len(plaid_transactions) > 0:
                logger.info(f"   - First transaction: {plaid_transactions[0].get('transaction_id', 'N/A')} - {plaid_transactions[0].get('amount', 'N/A')}")
                logger.info(f"   - Last transaction: {plaid_transactions[-1].get('transaction_id', 'N/A')} - {plaid_transactions[-1].get('amount', 'N/A')}")
            else:
                logger.warning(f"⚠️  DEBUG: No transactions returned from Plaid API!")
            
            # Process transactions
            result = await self._process_account_transactions(
                account, plaid_transactions, db
            )
            
            # Update account sync status
            account.sync_status = 'synced'
            account.last_sync_at = datetime.now(timezone.utc)
            account.connection_health = 'healthy'
            account.last_sync_error = None
            
            # Update metadata
            metadata = account.account_metadata or {}
            metadata['last_transaction_sync'] = datetime.now(timezone.utc).isoformat()
            metadata['last_sync_transaction_count'] = result.new_transactions
            account.account_metadata = metadata
            
            db.add(account)
            db.commit()
            
            # Calculate sync duration
            sync_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.sync_duration_seconds = sync_duration
            result.date_range = f"{start_date.date()} to {end_date.date()}"
            
            # Send notification
            await self._send_sync_completion_notification(account, result)
            
            logger.info(f"Transaction sync completed for {account.name}: "
                       f"{result.new_transactions} new, {result.updated_transactions} updated")
            
            return result
            
        except Exception as e:
            # Update account with error status
            try:
                account = db.query(Account).filter(Account.id == account_id).first()
                if account:
                    account.sync_status = 'error'
                    account.last_sync_error = str(e)
                    account.connection_health = 'failed'
                    db.add(account)
                    db.commit()
            except:
                pass
            
            logger.error(f"Transaction sync failed for account {account_id}: {e}")
            raise
            
        finally:
            # Always release the distributed lock
            await self._release_sync_lock(account_id)
    
    async def sync_user_transactions(
        self, 
        user_id: str, 
        db: Session,
        days: int = None
    ) -> Dict[str, Any]:
        """Sync transactions for all user's connected accounts"""
        
        accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.plaid_access_token.isnot(None),
            Account.is_active == True
        ).all()
        
        if not accounts:
            return {
                'success': True,
                'message': 'No connected accounts to sync',
                'results': []
            }
        
        results = []
        total_new = 0
        total_updated = 0
        total_errors = 0
        
        # Sync accounts concurrently (but with rate limiting)
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent syncs
        
        async def sync_single_account(account):
            async with semaphore:
                try:
                    result = await self.sync_account_transactions(
                        str(account.id), db, days
                    )
                    return {
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'success': True,
                        'result': result
                    }
                except Exception as e:
                    return {
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'success': False,
                        'error': str(e)
                    }
        
        # Execute syncs
        tasks = [sync_single_account(account) for account in accounts]
        sync_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in sync_results:
            if isinstance(result, Exception):
                total_errors += 1
                results.append({
                    'success': False,
                    'error': str(result)
                })
            else:
                results.append(result)
                if result['success']:
                    sync_result = result['result']
                    total_new += sync_result.new_transactions
                    total_updated += sync_result.updated_transactions
                else:
                    total_errors += 1
        
        # Send summary notification
        await self._send_bulk_sync_notification(user_id, total_new, total_updated, total_errors)
        
        return {
            'success': True,
            'accounts_synced': len(accounts),
            'total_new_transactions': total_new,
            'total_updated_transactions': total_updated,
            'total_errors': total_errors,
            'results': results
        }
    
    async def _process_account_transactions(
        self, 
        account: Account, 
        plaid_transactions: List[Dict[str, Any]], 
        db: Session
    ) -> SyncResult:
        """Process Plaid transactions for an account"""
        
        logger.info(f"🔄 DEBUG: Processing {len(plaid_transactions)} transactions for account {account.name}")
        
        # DEBUG: Log detailed transaction info if any exist
        if plaid_transactions:
            for i, tx in enumerate(plaid_transactions[:3]):  # Log first 3 transactions
                logger.info(f"   📋 Transaction {i+1}: ID={tx.get('transaction_id', 'N/A')}, Amount=${tx.get('amount', 'N/A')}, Date={tx.get('date', 'N/A')}, Name='{tx.get('name', 'N/A')}'")
        
        result = SyncResult(
            account_id=str(account.id),
            new_transactions=0,
            updated_transactions=0,
            duplicates_skipped=0,
            errors=[],
            sync_duration_seconds=0,
            date_range=""
        )
        
        # Get existing Plaid transaction IDs to avoid duplicates
        existing_plaid_ids = set(
            row[0] for row in db.query(Transaction.plaid_transaction_id)
            .filter(
                Transaction.account_id == account.id,
                Transaction.plaid_transaction_id.isnot(None)
            )
            .all()
        )
        
        logger.info(f"🔍 DEBUG: Found {len(existing_plaid_ids)} existing Plaid transaction IDs in database")
        if len(existing_plaid_ids) > 0:
            logger.info(f"   - Sample existing IDs: {list(existing_plaid_ids)[:3]}")
        else:
            logger.info(f"   - No existing Plaid transactions found - this should be a fresh sync")
        
        # Process transactions in batches
        logger.info(f"📝 DEBUG: Processing {len(plaid_transactions)} transactions in batches of {self.batch_size}")
        
        for i in range(0, len(plaid_transactions), self.batch_size):
            batch = plaid_transactions[i:i + self.batch_size]
            logger.info(f"   - Processing batch {i//self.batch_size + 1} with {len(batch)} transactions")
            
            for j, plaid_txn in enumerate(batch):
                try:
                    plaid_id = plaid_txn.get('transaction_id')
                    amount = plaid_txn.get('amount', 0)
                    description = plaid_txn.get('name', 'Unknown')
                    
                    logger.info(f"     Transaction {j+1}: {plaid_id} - ${amount} - {description}")
                    
                    if plaid_id in existing_plaid_ids:
                        logger.info(f"       ⏭️  SKIPPED - Already exists in database")
                        result.duplicates_skipped += 1
                        continue
                    
                    # Create new transaction
                    logger.info(f"       💾 CREATING - New transaction")
                    transaction = await self._create_transaction_from_plaid(
                        plaid_txn, account, db
                    )
                    
                    if transaction:
                        logger.info(f"       ✅ SUCCESS - Transaction created with ID: {transaction.id}")
                        result.new_transactions += 1
                        existing_plaid_ids.add(plaid_id)
                    else:
                        logger.warning(f"       ⚠️  FAILED - Transaction creation returned None")
                
                except Exception as e:
                    error_msg = f"Failed to process transaction {plaid_txn.get('transaction_id', 'unknown')}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(f"       ❌ ERROR - {error_msg}")
        
        # Commit batch
        logger.info(f"💾 DEBUG: Committing transactions to database...")
        try:
            db.commit()
            logger.info(f"✅ DEBUG: Database commit successful")
        except Exception as e:
            logger.error(f"❌ DEBUG: Database commit failed: {str(e)}")
            db.rollback()
            raise Exception(f"Failed to commit transactions: {str(e)}")
        
        # Final summary
        logger.info(f"🏁 DEBUG: Transaction sync complete for {account.name}:")
        logger.info(f"   - New transactions: {result.new_transactions}")
        logger.info(f"   - Updated transactions: {result.updated_transactions}")
        logger.info(f"   - Duplicates skipped: {result.duplicates_skipped}")
        logger.info(f"   - Errors: {len(result.errors)}")
        
        return result
    
    async def _create_transaction_from_plaid(
        self, 
        plaid_txn: Dict[str, Any], 
        account: Account, 
        db: Session
    ) -> Optional[Transaction]:
        """Create a transaction from Plaid data with enhanced processing"""
        
        try:
            # Parse amount - Plaid's sign convention varies by account type
            raw_amount = float(plaid_txn.get('amount', 0))
            
            # Convert amount based on account type and Plaid's conventions
            amount_cents = self._convert_plaid_amount(raw_amount, account.account_type)
            
            # Enhanced debug logging
            transaction_type = "INCOME" if amount_cents > 0 else "EXPENSE"
            logger.info(f"       💰 AMOUNT DEBUG: Account type: {account.account_type}")
            logger.info(f"       💰 AMOUNT DEBUG: Raw Plaid amount: {raw_amount} → Converted: {amount_cents/100} (cents: {amount_cents}) → Type: {transaction_type}")
            
            # Parse dates
            transaction_date = self._parse_date(plaid_txn.get('date'))
            authorized_date = self._parse_date(plaid_txn.get('authorized_date'))
            
            # Extract merchant information
            merchant_name = None
            merchant_logo = None
            
            if 'merchant_name' in plaid_txn:
                merchant_name = plaid_txn['merchant_name']
            elif plaid_txn.get('counterparties'):
                counterparty = plaid_txn['counterparties'][0]
                merchant_name = counterparty.get('name')
                if counterparty.get('logo_url'):
                    merchant_logo = counterparty['logo_url']
            
            # Determine transaction status
            status = 'posted'
            if plaid_txn.get('pending'):
                status = 'pending'
            elif plaid_txn.get('pending_transaction_id'):
                status = 'posted'  # This is an update to a pending transaction
            
            # Enhanced metadata
            metadata = {
                'plaid_data': plaid_txn,
                'imported_at': datetime.now(timezone.utc).isoformat(),
                'sync_method': 'automatic',
                'account_owner': plaid_txn.get('account_owner'),
                'iso_currency_code': plaid_txn.get('iso_currency_code'),
                'unofficial_currency_code': plaid_txn.get('unofficial_currency_code'),
                'personal_finance_category': plaid_txn.get('personal_finance_category')
            }
            
            # Add location data if available
            if plaid_txn.get('location'):
                metadata['location'] = plaid_txn['location']
            
            # Add payment channel information
            if plaid_txn.get('payment_channel'):
                metadata['payment_channel'] = plaid_txn['payment_channel']
            
            transaction_create = TransactionCreate(
                user_id=account.user_id,
                account_id=account.id,
                amount_cents=amount_cents,
                currency=plaid_txn.get('iso_currency_code', account.currency),
                description=plaid_txn.get('name', 'Unknown Transaction'),
                merchant=merchant_name,
                merchant_logo=merchant_logo,
                transaction_date=transaction_date,
                authorized_date=authorized_date,
                status=status,
                plaid_transaction_id=plaid_txn.get('transaction_id'),
                plaid_category=plaid_txn.get('category', []),
                metadata_json=metadata
            )
            
            transaction = await self.transaction_service.create_transaction(db=db, transaction=transaction_create, user_id=account.user_id)
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to create transaction from Plaid data: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        try:
            return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        except:
            try:
                # Try parsing as date only
                from dateutil.parser import parse
                return parse(date_str).replace(tzinfo=timezone.utc)
            except:
                return None
    
    def _calculate_sync_days(self, account: Account, force_sync: bool = False) -> int:
        """Calculate how many days of transactions to sync"""
        
        if force_sync:
            return self.max_sync_days
        
        if not account.last_sync_at:
            # First sync - get default period
            return self.default_sync_days
        
        # Calculate days since last sync
        days_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).days
        
        # Sync at least the days since last sync, plus a buffer
        sync_days = min(days_since_sync + 1, self.max_sync_days)
        
        return max(sync_days, 1)  # At least 1 day
    
    async def _send_sync_completion_notification(self, account: Account, result: SyncResult):
        """Send notification when sync completes"""
        try:
            await websocket_manager.send_user_event(
                str(account.user_id),
                WebSocketEvent(
                    type=EventType.TRANSACTION_SYNC_COMPLETE,
                    data={
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'new_transactions': result.new_transactions,
                        'updated_transactions': result.updated_transactions,
                        'duplicates_skipped': result.duplicates_skipped,
                        'sync_duration': result.sync_duration_seconds,
                        'date_range': result.date_range
                    }
                )
            )
        except Exception as e:
            logger.error(f"Failed to send sync completion notification: {e}")
    
    async def _send_bulk_sync_notification(
        self, 
        user_id: str, 
        total_new: int, 
        total_updated: int, 
        total_errors: int
    ):
        """Send notification for bulk sync completion"""
        try:
            await websocket_manager.send_user_event(
                user_id,
                WebSocketEvent(
                    type=EventType.BULK_SYNC_COMPLETE,
                    data={
                        'total_new_transactions': total_new,
                        'total_updated_transactions': total_updated,
                        'total_errors': total_errors,
                        'sync_time': datetime.now(timezone.utc).isoformat()
                    }
                )
            )
        except Exception as e:
            logger.error(f"Failed to send bulk sync notification: {e}")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status by querying Redis for active locks"""
        try:
            conn = await redis_client.get_connection()
            
            # Get all sync lock keys
            lock_keys = await conn.keys("sync-lock:*")
            
            # Extract account IDs from lock keys
            syncing_accounts = []
            for key in lock_keys:
                if key.startswith("sync-lock:"):
                    account_id = key[10:]  # Remove "sync-lock:" prefix
                    syncing_accounts.append(account_id)
            
            await conn.close()
            
            return {
                'active_syncs': len(syncing_accounts),
                'syncing_accounts': syncing_accounts,
                'plaid_service_status': await self.plaid_service.get_sync_status()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status from Redis: {str(e)}")
            return {
                'active_syncs': 0,
                'syncing_accounts': [],
                'error': f"Failed to get sync status: {str(e)}",
                'plaid_service_status': await self.plaid_service.get_sync_status()
            }
    
    async def schedule_automatic_sync(self, db: Session, user_id: Optional[str] = None):
        """Schedule automatic sync for accounts that need it"""
        
        # Find accounts that need sync
        query = db.query(Account).filter(
            Account.plaid_access_token.isnot(None),
            Account.is_active == True,
            Account.sync_status != 'syncing'
        )
        
        if user_id:
            query = query.filter(Account.user_id == user_id)
        
        accounts_needing_sync = [
            account for account in query.all()
            if account.needs_sync
        ]
        
        if not accounts_needing_sync:
            return {
                'scheduled_syncs': 0,
                'message': 'No accounts need synchronization'
            }
        
        # Group by user to minimize notifications
        user_accounts = defaultdict(list)
        for account in accounts_needing_sync:
            user_accounts[str(account.user_id)].append(account)
        
        scheduled_count = 0
        
        # Schedule syncs per user
        for user_id, accounts in user_accounts.items():
            try:
                # Schedule background sync
                asyncio.create_task(
                    self.sync_user_transactions(user_id, db, days=7)
                )
                scheduled_count += len(accounts)
                
            except Exception as e:
                logger.error(f"Failed to schedule sync for user {user_id}: {e}")
        
        return {
            'scheduled_syncs': scheduled_count,
            'users_affected': len(user_accounts),
            'message': f'Scheduled sync for {scheduled_count} accounts'
        }
    
    async def sync_transactions_for_item(self, db: Session, item_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Syncs transactions for all accounts connected to a specific Plaid Item.
        This method is specifically designed for webhook-triggered syncs.
        """
        from app.models.account import Account
        
        try:
            # Find all accounts for this Plaid item
            accounts_to_sync = db.query(Account).filter(
                Account.plaid_item_id == item_id,
                Account.is_active == True
            ).all()
            
            if not accounts_to_sync:
                logger.warning(f"Received webhook for unknown or inactive item_id: {item_id}")
                return {
                    'success': False,
                    'error': f'No active accounts found for item_id: {item_id}',
                    'accounts_synced': 0
                }

            user_id = accounts_to_sync[0].user_id
            logger.info(f"Webhook-triggered sync for user {user_id}, item {item_id}, {len(accounts_to_sync)} accounts")
            
            # Mark all accounts as syncing
            for account in accounts_to_sync:
                account.sync_status = 'syncing'
                db.add(account)
            db.commit()
            
            # Use the existing user transaction sync method
            result = await self.sync_user_transactions(
                user_id=str(user_id), 
                db=db, 
                days=days
            )
            
            # Add webhook-specific metadata
            result['trigger'] = 'webhook'
            result['item_id'] = item_id
            result['webhook_sync_time'] = datetime.now(timezone.utc).isoformat()
            
            # Send WebSocket notification for real-time updates
            await self._send_webhook_sync_notification(user_id, item_id, result)
            
            logger.info(f"Webhook sync completed for item {item_id}: "
                       f"{result.get('total_new_transactions', 0)} new transactions")
            
            return result
            
        except Exception as e:
            logger.error(f"Webhook-triggered sync failed for item {item_id}: {e}")
            
            # Update account statuses on failure
            try:
                accounts_to_sync = db.query(Account).filter(Account.plaid_item_id == item_id).all()
                for account in accounts_to_sync:
                    account.sync_status = 'error'
                    account.last_sync_error = f"Webhook sync failed: {str(e)}"
                    account.connection_health = 'failed'
                    db.add(account)
                db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update account statuses after webhook sync failure: {update_error}")
            
            return {
                'success': False,
                'error': str(e),
                'trigger': 'webhook',
                'item_id': item_id,
                'accounts_synced': 0
            }
    
    async def _send_webhook_sync_notification(self, user_id: str, item_id: str, result: Dict[str, Any]):
        """Send notification for webhook-triggered sync completion"""
        try:
            await websocket_manager.send_user_event(
                str(user_id),
                WebSocketEvent(
                    type=EventType.WEBHOOK_SYNC_COMPLETE,
                    data={
                        'item_id': item_id,
                        'total_new_transactions': result.get('total_new_transactions', 0),
                        'total_updated_transactions': result.get('total_updated_transactions', 0),
                        'accounts_synced': result.get('accounts_synced', 0),
                        'sync_time': result.get('webhook_sync_time'),
                        'success': result.get('success', True)
                    }
                )
            )
            logger.info(f"Sent webhook sync notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send webhook sync notification: {e}")
    
    def _convert_plaid_amount(self, raw_amount: float, account_type: str) -> int:
        """
        Convert Plaid transaction amount to our system's amount_cents format.
        
        Plaid's amount conventions:
        - Depository accounts (checking, savings): positive = outflow, negative = inflow
        - Credit accounts: positive = charges, negative = payments
        - Investment accounts: positive = outflow, negative = inflow
        
        Our system: positive = income, negative = expenses
        """
        
        # Normalize account type for comparison
        account_type_lower = account_type.lower()
        
        # Convert to cents first
        amount_cents = int(raw_amount * 100)
        
        if account_type_lower in ['checking', 'savings', 'depository', 'money_market']:
            # Depository accounts: Plaid positive = outflow (expense), negative = inflow (income)
            # So we need to invert: Plaid positive becomes our negative
            return -amount_cents
            
        elif account_type_lower in ['credit', 'credit_card', 'credit_line']:
            # Credit accounts: Plaid positive = charges (expense), negative = payments (income to user)  
            # So we need to invert: Plaid positive becomes our negative
            return -amount_cents
            
        elif account_type_lower in ['investment', 'brokerage']:
            # Investment accounts: similar to depository
            # Plaid positive = money out (expense), negative = money in (income)
            return -amount_cents
            
        else:
            # Default behavior for unknown account types: invert sign
            # Log this case for investigation
            logger.warning(f"Unknown account type '{account_type}' - using default amount conversion")
            return -amount_cents

# Create global service instance
transaction_sync_service = TransactionSyncService()