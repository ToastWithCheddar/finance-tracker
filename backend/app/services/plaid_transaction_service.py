"""
Plaid Transaction Service
Handles transaction synchronization, processing, and management from Plaid
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone, date
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate
from app.services.transaction_service import TransactionService
from app.services.plaid_client_service import plaid_client_service
from app.services.utils.plaid_utils import group_accounts_by_token
from app.websocket.manager import redis_websocket_manager as websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)


class PlaidTransactionService:
    """Service for managing Plaid transaction synchronization"""
    
    def __init__(self):
        self.transaction_service = TransactionService()
    
    async def sync_transactions_for_user(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Efficiently syncs transactions for all of a user's Plaid-connected accounts,
        grouping by connection to minimize API calls and avoid rate limiting.
        """
        
        # Get all Plaid-connected accounts for the user
        user_accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.plaid_access_token_encrypted.isnot(None)
        ).all()

        if not user_accounts:
            return {"success": True, "message": "No Plaid accounts to sync.", "results": []}

        # Group accounts by access token (Item)
        token_groups = group_accounts_by_token(user_accounts)

        # Process each group
        overall_results = {
            "success": True,
            "accounts_synced": len(user_accounts),
            "total_new_transactions": 0,
            "total_updated_transactions": 0,
            "total_errors": 0,
            "results": []
        }

        for access_token, accounts_in_group in token_groups.items():
            start_time = time.time()
            try:
                # Define date range for sync (e.g., last 90 days)
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=90)
                
                plaid_account_ids = [acc.plaid_account_id for acc in accounts_in_group]

                # Fetch transactions for all accounts in the group with ONE API call
                plaid_data = await self.fetch_transactions(
                    access_token, start_date, end_date, plaid_account_ids
                )
                
                # Process the fetched transactions
                synced_count = await self._process_transactions(
                    plaid_data.get('transactions', []), accounts_in_group, db
                )

                overall_results["total_new_transactions"] += synced_count
                
                # Report success for each account in the group
                for account in accounts_in_group:
                    overall_results["results"].append({
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "success": True,
                        "result": { 
                            "new_transactions": synced_count, 
                            "sync_duration_seconds": time.time() - start_time 
                        }
                    })

            except Exception as e:
                logger.error(f"Failed to sync transactions for token group: {e}", exc_info=True)
                overall_results["total_errors"] += len(accounts_in_group)
                # Report failure for each account in the group
                for account in accounts_in_group:
                     overall_results["results"].append({
                        "account_id": str(account.id), 
                        "account_name": account.name, 
                        "success": False, 
                        "error": str(e)
                    })
            
            # Add a small delay between processing each token to be a good API citizen
            await asyncio.sleep(1) # 1-second delay

        # Send a final completion event via WebSocket to trigger a dashboard refresh
        try:
            completion_event = WebSocketEvent(
                type=EventType.DASHBOARD_UPDATE,
                data={
                    "event": "sync_completed",
                    "details": overall_results
                }
            )
            await websocket_manager.send_to_user(str(user_id), completion_event.to_dict())
            logger.info(f"Sent DASHBOARD_UPDATE (sync_completed) event to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send DASHBOARD_UPDATE event to user {user_id}: {e}", exc_info=True)

        return overall_results

    async def initial_transaction_sync(self, accounts: List[Account], access_token: str, db: Session):
        """Perform initial transaction sync for new accounts"""
        try:
            # Sync last 30 days of transactions
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
            end_date = datetime.now(timezone.utc)
            
            account_ids = [acc.plaid_account_id for acc in accounts]
            
            transactions_result = await self.fetch_transactions(
                access_token, start_date, end_date, account_ids
            )
            
            synced_count = await self._process_transactions(
                transactions_result.get('transactions', []), accounts, db
            )
            
            logger.info(f"Initial sync: imported {synced_count} transactions for {len(accounts)} accounts")
            
        except Exception as e:
            logger.error(f"Initial transaction sync failed: {e}")
    
    async def fetch_transactions(
        self, 
        access_token: str, 
        start_date: datetime, 
        end_date: datetime,
        account_ids: Optional[List[str]] = None,
        count: int = 500
    ) -> Dict[str, Any]:
        """Fetch transactions from Plaid with pagination"""
        
        all_transactions = []
        offset = 0
        
        try:
            while True:
                result = await plaid_client_service.fetch_transactions(
                    access_token=access_token,
                    start_date=start_date.date().isoformat(),
                    end_date=end_date.date().isoformat(),
                    count=count,
                    offset=offset,
                    account_ids=account_ids
                )
                
                if not result.get('success'):
                    raise Exception(result.get('error', 'Failed to fetch transactions'))
                
                transactions = result.get('transactions', [])
                
                # DEBUG: Log what Plaid returned
                logger.info(f"🔍 PLAID DEBUG: API Response:")
                logger.info(f"   - Total transactions available: {result.get('total_transactions', 'Unknown')}")
                logger.info(f"   - Transactions in this batch: {len(transactions)}")
                logger.info(f"   - Current offset: {offset}")
                
                if transactions:
                    # Log first transaction as example
                    first_tx = transactions[0]
                    logger.info(f"   - Example transaction: {first_tx.get('transaction_id', 'No ID')} - ${first_tx.get('amount', 0)} - {first_tx.get('name', 'No name')}")
                else:
                    logger.info(f"   - No transactions returned by Plaid API")
                
                if not transactions:
                    break
                
                all_transactions.extend(transactions)
                
                # Check pagination
                total_transactions = result.get('total_transactions', 0)
                if len(all_transactions) >= total_transactions:
                    break
                
                offset += len(transactions)
                
                # Prevent infinite loop
                if offset > 10000:  # Reasonable limit
                    break
            
            # DEBUG: Log final result summary
            logger.info(f"🔍 PLAID DEBUG: Final fetch_transactions result:")
            logger.info(f"   - Total transactions fetched: {len(all_transactions)}")
            if all_transactions:
                logger.info(f"   - Date range of fetched transactions: {min(tx.get('date', '') for tx in all_transactions)} to {max(tx.get('date', '') for tx in all_transactions)}")
            
            return {
                'transactions': all_transactions,
                'accounts': result.get('accounts', []),
                'total': len(all_transactions)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            raise
    
    async def _process_transactions(
        self, 
        plaid_transactions: List[Dict[str, Any]], 
        accounts: List[Account], 
        db: Session
    ) -> int:
        """Process and save Plaid transactions to database"""
        
        # Create account ID mapping
        account_map = {acc.plaid_account_id: acc for acc in accounts}
        synced_count = 0
        
        for plaid_txn in plaid_transactions:
            try:
                # Get the corresponding account
                plaid_account_id = plaid_txn.get('account_id')
                account = account_map.get(plaid_account_id)
                
                if not account:
                    logger.warning(f"Account not found for Plaid transaction: {plaid_account_id}")
                    continue
                
                # Check if transaction already exists
                existing = db.query(Transaction).filter(
                    Transaction.plaid_transaction_id == plaid_txn.get('transaction_id')
                ).first()
                
                if existing:
                    # Update existing transaction if needed
                    if self._should_update_transaction(existing, plaid_txn):
                        await self._update_transaction_from_plaid(existing, plaid_txn, db)
                    continue
                
                # Create new transaction
                transaction = await self._create_transaction_from_plaid(plaid_txn, account, db)
                if transaction:
                    synced_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process transaction {plaid_txn.get('transaction_id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(plaid_transactions)} Plaid transactions, created {synced_count} new transactions")
        return synced_count
    
    async def _create_transaction_from_plaid(
        self, 
        plaid_txn: Dict[str, Any], 
        account: Account, 
        db: Session
    ) -> Optional[Transaction]:
        """Create a new transaction from Plaid data"""
        
        try:
            # Convert Plaid amount (positive for outflow) to our format (negative for expenses)
            plaid_amount = plaid_txn.get('amount', 0)
            amount_cents = int(-plaid_amount * 100)  # Negate and convert to cents
            
            # Determine transaction type
            transaction_type = self._determine_transaction_type(plaid_txn, plaid_amount)
            
            # Extract merchant information
            merchant_name = None
            if plaid_txn.get('merchant_name'):
                merchant_name = plaid_txn['merchant_name']
            elif plaid_txn.get('name'):
                merchant_name = plaid_txn['name']
            
            # Create transaction metadata
            metadata = {
                'plaid_transaction_id': plaid_txn.get('transaction_id'),
                'plaid_account_id': plaid_txn.get('account_id'),
                'plaid_category': plaid_txn.get('category', []),
                'plaid_category_id': plaid_txn.get('category_id'),
                'plaid_original_description': plaid_txn.get('original_description'),
                'plaid_pending': plaid_txn.get('pending', False),
                'plaid_authorized_date': plaid_txn.get('authorized_date'),
                'plaid_location': plaid_txn.get('location'),
                'plaid_payment_meta': plaid_txn.get('payment_meta'),
                'sync_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Create TransactionCreate object
            transaction_create = TransactionCreate(
                account_id=account.id,
                amount_cents=amount_cents,
                currency=plaid_txn.get('iso_currency_code', 'USD'),
                description=plaid_txn.get('name', 'Unknown Transaction'),
                merchant=merchant_name,
                transaction_date=datetime.strptime(plaid_txn.get('date'), '%Y-%m-%d').date(),
                status='posted' if not plaid_txn.get('pending', False) else 'pending',
                is_recurring=False,  # Will be detected separately
                is_transfer=transaction_type == 'transfer',
                notes=f"Imported from Plaid: {plaid_txn.get('original_description', '')}",
                plaid_transaction_id=plaid_txn.get('transaction_id'),
                metadata_json=metadata
            )
            
            # Create transaction through service (includes ML categorization)
            transaction = await self.transaction_service.create_transaction(
                db=db, 
                transaction=transaction_create, 
                user_id=account.user_id
            )
            
            logger.debug(f"Created transaction: {transaction.description} - ${amount_cents/100}")
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to create transaction from Plaid data: {e}")
            return None
    
    async def _update_transaction_from_plaid(
        self, 
        transaction: Transaction, 
        plaid_txn: Dict[str, Any], 
        db: Session
    ) -> None:
        """Update existing transaction with fresh Plaid data"""
        
        try:
            # Update basic fields that might have changed
            plaid_amount = plaid_txn.get('amount', 0)
            transaction.amount_cents = int(-plaid_amount * 100)
            transaction.description = plaid_txn.get('name', transaction.description)
            transaction.status = 'posted' if not plaid_txn.get('pending', False) else 'pending'
            
            # Update metadata
            metadata = transaction.metadata_json or {}
            metadata.update({
                'plaid_pending': plaid_txn.get('pending', False),
                'plaid_authorized_date': plaid_txn.get('authorized_date'),
                'last_sync': datetime.now(timezone.utc).isoformat()
            })
            transaction.metadata_json = metadata
            
            db.add(transaction)
            db.commit()
            
            logger.debug(f"Updated transaction: {transaction.description}")
            
        except Exception as e:
            logger.error(f"Failed to update transaction {transaction.id}: {e}")
    
    def _should_update_transaction(self, transaction: Transaction, plaid_txn: Dict[str, Any]) -> bool:
        """Check if an existing transaction should be updated with new Plaid data"""
        
        # Update if status changed (pending to posted)
        current_pending = transaction.metadata_json.get('plaid_pending', False) if transaction.metadata_json else False
        new_pending = plaid_txn.get('pending', False)
        
        if current_pending != new_pending:
            return True
        
        # Update if amount changed (rare but possible)
        plaid_amount = plaid_txn.get('amount', 0)
        new_amount_cents = int(-plaid_amount * 100)
        
        if transaction.amount_cents != new_amount_cents:
            return True
        
        return False
    
    def _determine_transaction_type(self, plaid_txn: Dict[str, Any], amount: float) -> str:
        """Determine transaction type from Plaid data"""
        
        categories = plaid_txn.get('category', [])
        
        # Check for transfers
        if 'Transfer' in categories:
            return 'transfer'
        
        # Check for deposits/income
        if amount < 0 or 'Deposit' in categories:  # Plaid uses negative for inflow
            return 'income'
        
        # Default to expense
        return 'expense'
    


# Create singleton instance
plaid_transaction_service = PlaidTransactionService()