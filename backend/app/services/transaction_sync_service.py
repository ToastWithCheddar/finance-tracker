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
from app.websocket.manager import websocket_manager
from app.websocket.events import WebSocketEvent, EventType

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
        
        # Track ongoing syncs to prevent duplicates
        self.active_syncs: Set[str] = set()
    
    async def sync_account_transactions(
        self, 
        account_id: str, 
        db: Session,
        days: int = None,
        force_sync: bool = False
    ) -> SyncResult:
        """Sync transactions for a single account"""
        
        if account_id in self.active_syncs:
            raise Exception(f"Account {account_id} is already being synced")
        
        self.active_syncs.add(account_id)
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
            
            # Update account sync status
            account.sync_status = 'syncing'
            db.add(account)
            db.commit()
            
            # Fetch transactions from Plaid
            transactions_data = await self.plaid_service.fetch_transactions(
                account.plaid_access_token,
                start_date,
                end_date,
                [account.plaid_account_id]
            )
            
            # Process transactions
            result = await self._process_account_transactions(
                account, transactions_data.get('transactions', []), db
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
            self.active_syncs.discard(account_id)
    
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
            db.query(Transaction.plaid_transaction_id)
            .filter(
                Transaction.account_id == account.id,
                Transaction.plaid_transaction_id.isnot(None)
            )
            .scalars()
            .all()
        )
        
        # Process transactions in batches
        for i in range(0, len(plaid_transactions), self.batch_size):
            batch = plaid_transactions[i:i + self.batch_size]
            
            for plaid_txn in batch:
                try:
                    plaid_id = plaid_txn.get('transaction_id')
                    
                    if plaid_id in existing_plaid_ids:
                        result.duplicates_skipped += 1
                        continue
                    
                    # Create new transaction
                    transaction = await self._create_transaction_from_plaid(
                        plaid_txn, account, db
                    )
                    
                    if transaction:
                        result.new_transactions += 1
                        existing_plaid_ids.add(plaid_id)
                
                except Exception as e:
                    error_msg = f"Failed to process transaction {plaid_txn.get('transaction_id', 'unknown')}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)
        
        # Commit batch
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to commit transactions: {str(e)}")
        
        return result
    
    async def _create_transaction_from_plaid(
        self, 
        plaid_txn: Dict[str, Any], 
        account: Account, 
        db: Session
    ) -> Optional[Transaction]:
        """Create a transaction from Plaid data with enhanced processing"""
        
        try:
            # Parse amount (Plaid uses positive for debits, negative for credits)
            amount = float(plaid_txn.get('amount', 0))
            amount_cents = int(-amount * 100)  # Invert sign for our system
            
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
            
            transaction = self.transaction_service.create(db=db, obj_in=transaction_create)
            
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
        """Get current sync status"""
        return {
            'active_syncs': len(self.active_syncs),
            'syncing_accounts': list(self.active_syncs),
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

# Create global service instance
transaction_sync_service = TransactionSyncService()