"""
Plaid Transaction Service
Handles transaction synchronization, processing, and management from Plaid
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate
from app.services.transaction_service import get_transaction_service
from app.services.plaid_client_service import get_plaid_client_service

logger = logging.getLogger(__name__)


class PlaidTransactionService:
    """
    Lightweight service for Plaid transaction data fetching and processing.
    For full transaction synchronization with locking, use TransactionSyncService.
    """
    
    def __init__(self):
        self.transaction_service = get_transaction_service()
    
    # Removed sync_transactions_for_user - this functionality has been moved to TransactionSyncService
    # to avoid duplication and provide better orchestration with locking, metrics, and notifications.

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
        account_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fetch transactions from Plaid (simplified without pagination)"""
        
        try:
            result = await get_plaid_client_service().fetch_transactions(
                access_token=access_token,
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
                account_ids=account_ids
            )
            
            if not result.get('success'):
                raise Exception(result.get('error', 'Failed to fetch transactions'))
            
            transactions = result.get('transactions', [])
            
            # DEBUG: Log what Plaid returned
            logger.info(f"🔍 PLAID DEBUG: API Response:")
            logger.info(f"   - Total transactions available: {result.get('total_transactions', 'Unknown')}")
            logger.info(f"   - Transactions in this batch: {len(transactions)}")
            
            if transactions:
                # Log first transaction as example
                first_tx = transactions[0]
                logger.info(f"   - Example transaction: {first_tx.get('transaction_id', 'No ID')} - ${first_tx.get('amount', 0)} - {first_tx.get('name', 'No name')}")
            else:
                logger.info(f"   - No transactions returned by Plaid API")
            
            # DEBUG: Log final result summary
            logger.info(f"🔍 PLAID DEBUG: Final fetch_transactions result:")
            logger.info(f"   - Total transactions fetched: {len(transactions)}")
            if transactions:
                logger.info(f"   - Date range of fetched transactions: {min(tx.get('date', '') for tx in transactions)} to {max(tx.get('date', '') for tx in transactions)}")
            
            return {
                'transactions': transactions,
                'accounts': result.get('accounts', []),
                'total': len(transactions)
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
    


# Provider function with lazy caching
_plaid_transaction_service_instance = None

def get_plaid_transaction_service() -> PlaidTransactionService:
    """Get the global PlaidTransactionService instance with lazy initialization"""
    global _plaid_transaction_service_instance
    if _plaid_transaction_service_instance is None:
        _plaid_transaction_service_instance = PlaidTransactionService()
    return _plaid_transaction_service_instance
