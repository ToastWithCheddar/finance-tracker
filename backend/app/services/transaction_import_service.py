"""
Automatic transaction import service for Plaid integration
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.transaction import TransactionCreate
from app.services.transaction_service import TransactionService
from app.services.plaid_service import plaid_service
from app.websocket.events import WebSocketEvent, EventType
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

class TransactionImportService:
    """Service for automatic transaction import from bank accounts"""
    
    def __init__(self):
        self.transaction_service = TransactionService()
        
    async def import_transactions_for_account(
        self, 
        db: Session, 
        account_id: str, 
        days_back: int = 30,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Import transactions for a specific account"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            if not account.plaid_access_token:
                raise ValueError(f"Account {account_id} is not connected to Plaid")
            
            # Determine date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Get last import date if available
            metadata = account.account_metadata or {}
            last_import = metadata.get('last_transaction_import')
            if last_import:
                last_import_date = datetime.fromisoformat(last_import.replace('Z', ''))
                # Only import transactions since last import, but ensure at least 1 day back
                start_date = max(last_import_date - timedelta(days=1), start_date)
            
            # Fetch transactions from Plaid
            plaid_transactions = await plaid_service.fetch_transactions(
                account.plaid_access_token,
                start_date,
                end_date,
                [account.plaid_account_id]
            )
            
            # Process and import transactions
            import_results = await self._process_plaid_transactions(
                db, account, plaid_transactions.get('transactions', [])
            )
            
            # Update account metadata
            metadata['last_transaction_import'] = end_date.isoformat()
            metadata['transaction_import_count'] = metadata.get('transaction_import_count', 0) + import_results['imported']
            account.account_metadata = metadata
            db.add(account)
            db.commit()
            
            # Send real-time notification if we have a user_id
            if user_id and import_results['imported'] > 0:
                await websocket_manager.send_user_event(
                    user_id,
                    WebSocketEvent(
                        type=EventType.TRANSACTIONS_IMPORTED,
                        data={
                            "account_id": account_id,
                            "account_name": account.name,
                            "imported_count": import_results['imported'],
                            "duplicate_count": import_results['duplicates'],
                            "import_date": end_date.isoformat()
                        }
                    )
                )
            
            logger.info(f"Imported {import_results['imported']} transactions for account {account.name}")
            
            return {
                "account_id": account_id,
                "account_name": account.name,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                **import_results
            }
            
        except Exception as e:
            logger.error(f"Failed to import transactions for account {account_id}: {e}")
            raise
    
    async def _process_plaid_transactions(
        self, 
        db: Session, 
        account: Account, 
        plaid_transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and import Plaid transactions"""
        results = {
            'total_fetched': len(plaid_transactions),
            'imported': 0,
            'duplicates': 0,
            'failed': 0,
            'transactions': []
        }
        
        # Get existing Plaid transaction IDs to avoid duplicates
        existing_plaid_ids = set()
        existing_transactions = db.query(Transaction.plaid_transaction_id).filter(
            Transaction.account_id == account.id,
            Transaction.plaid_transaction_id.isnot(None)
        ).all()
        existing_plaid_ids.update(row[0] for row in existing_transactions)
        
        # Process each transaction
        for plaid_tx in plaid_transactions:
            try:
                plaid_id = plaid_tx.get('transaction_id')
                
                # Skip if already imported
                if plaid_id in existing_plaid_ids:
                    results['duplicates'] += 1
                    continue
                
                # Convert Plaid transaction to our format
                transaction_create = self._convert_plaid_transaction(account, plaid_tx)
                
                # Create transaction
                transaction = self.transaction_service.create(db=db, obj_in=transaction_create)
                
                results['imported'] += 1
                results['transactions'].append({
                    'id': str(transaction.id),
                    'amount': transaction.amount_cents / 100,
                    'description': transaction.description,
                    'date': transaction.transaction_date.isoformat(),
                    'plaid_id': plaid_id
                })
                
            except Exception as e:
                logger.error(f"Failed to process transaction {plaid_tx.get('transaction_id', 'unknown')}: {e}")
                results['failed'] += 1
        
        return results
    
    def _convert_plaid_transaction(self, account: Account, plaid_tx: Dict[str, Any]) -> TransactionCreate:
        """Convert Plaid transaction format to our TransactionCreate schema"""
        
        # Plaid amounts are positive for money going out (expenses) and negative for money coming in (income)
        # We'll store amounts as they come from Plaid (positive = expense, negative = income)
        amount_cents = int(plaid_tx.get('amount', 0) * -100)  # Invert for our system
        
        # Extract transaction date
        tx_date = plaid_tx.get('date')
        if isinstance(tx_date, str):
            transaction_date = datetime.strptime(tx_date, '%Y-%m-%d').date()
        else:
            transaction_date = date.today()
        
        # Extract authorized and posted dates if available
        authorized_date = plaid_tx.get('authorized_date')
        if authorized_date:
            authorized_date = datetime.strptime(authorized_date, '%Y-%m-%d').date()
        
        # Map Plaid categories to our system (this will be enhanced with ML later)
        plaid_categories = plaid_tx.get('category', [])
        category_id = None  # Will be determined by ML categorization service
        
        # Extract merchant information
        merchant_name = None
        merchant_logo = None
        if 'merchant_name' in plaid_tx:
            merchant_name = plaid_tx['merchant_name']
        elif 'name' in plaid_tx:
            merchant_name = plaid_tx['name']
        
        # Extract location if available
        location_data = None
        if 'location' in plaid_tx and plaid_tx['location']:
            location = plaid_tx['location']
            location_data = {
                'address': location.get('address'),
                'city': location.get('city'),
                'region': location.get('region'),
                'postal_code': location.get('postal_code'),
                'country': location.get('country'),
                'lat': location.get('lat'),
                'lon': location.get('lon')
            }
        
        # Build metadata
        metadata = {
            'plaid_account_id': plaid_tx.get('account_id'),
            'plaid_categories': plaid_categories,
            'import_source': 'plaid_auto',
            'import_date': datetime.utcnow().isoformat(),
            'original_description': plaid_tx.get('original_description'),
            'merchant_name': merchant_name,
            'iso_currency_code': plaid_tx.get('iso_currency_code', 'USD'),
            'unofficial_currency_code': plaid_tx.get('unofficial_currency_code')
        }
        
        if location_data:
            metadata['location'] = location_data
        
        return TransactionCreate(
            user_id=account.user_id,
            account_id=str(account.id),
            amount_cents=amount_cents,
            currency=plaid_tx.get('iso_currency_code', account.currency),
            description=plaid_tx.get('name', 'Unknown Transaction'),
            merchant=merchant_name,
            transaction_date=transaction_date,
            authorized_date=authorized_date,
            status='posted',  # Plaid transactions are typically posted
            location=location_data,
            plaid_transaction_id=plaid_tx.get('transaction_id'),
            plaid_category=plaid_categories,
            metadata_json=metadata
        )
    
    async def import_transactions_for_user(
        self, 
        db: Session, 
        user_id: str, 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Import transactions for all of a user's connected accounts"""
        try:
            # Get all Plaid-connected accounts for user
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.plaid_access_token.isnot(None),
                Account.is_active == True
            ).all()
            
            if not accounts:
                return {
                    "message": "No connected accounts found",
                    "accounts_processed": 0,
                    "total_imported": 0
                }
            
            results = {
                "accounts_processed": 0,
                "total_imported": 0,
                "total_duplicates": 0,
                "total_failed": 0,
                "account_results": []
            }
            
            # Process each account
            for account in accounts:
                try:
                    account_result = await self.import_transactions_for_account(
                        db, str(account.id), days_back, user_id
                    )
                    
                    results["accounts_processed"] += 1
                    results["total_imported"] += account_result.get("imported", 0)
                    results["total_duplicates"] += account_result.get("duplicates", 0)
                    results["total_failed"] += account_result.get("failed", 0)
                    results["account_results"].append(account_result)
                    
                except Exception as e:
                    logger.error(f"Failed to import transactions for account {account.id}: {e}")
                    results["account_results"].append({
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "error": str(e)
                    })
            
            # Send summary notification
            if results["total_imported"] > 0:
                await websocket_manager.send_user_event(
                    user_id,
                    WebSocketEvent(
                        type=EventType.BULK_IMPORT_COMPLETE,
                        data={
                            "total_imported": results["total_imported"],
                            "accounts_processed": results["accounts_processed"],
                            "import_date": datetime.utcnow().isoformat()
                        }
                    )
                )
            
            logger.info(f"Imported {results['total_imported']} transactions for user {user_id}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to import transactions for user {user_id}: {e}")
            raise
    
    async def schedule_automatic_imports(self, db: Session) -> Dict[str, Any]:
        """Schedule automatic imports for all active Plaid accounts"""
        try:
            # Get all accounts that need automatic import
            accounts = db.query(Account).filter(
                Account.plaid_access_token.isnot(None),
                Account.is_active == True
            ).all()
            
            # Group by user to avoid overwhelming individual users
            user_accounts = {}
            for account in accounts:
                user_id = account.user_id
                if user_id not in user_accounts:
                    user_accounts[user_id] = []
                user_accounts[user_id].append(account)
            
            results = {
                "users_processed": 0,
                "accounts_processed": 0,
                "total_imported": 0,
                "user_results": []
            }
            
            # Process each user's accounts
            for user_id, user_account_list in user_accounts.items():
                try:
                    user_result = await self.import_transactions_for_user(
                        db, user_id, days_back=7  # Weekly automatic import
                    )
                    
                    results["users_processed"] += 1
                    results["accounts_processed"] += user_result.get("accounts_processed", 0)
                    results["total_imported"] += user_result.get("total_imported", 0)
                    results["user_results"].append({
                        "user_id": user_id,
                        **user_result
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to import transactions for user {user_id}: {e}")
                    results["user_results"].append({
                        "user_id": user_id,
                        "error": str(e)
                    })
            
            logger.info(f"Automatic import complete: {results['total_imported']} transactions imported")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to schedule automatic imports: {e}")
            raise
    
    def get_import_history(self, db: Session, account_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get transaction import history for an account"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            # Get transactions that were imported from Plaid
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            imported_transactions = db.query(Transaction).filter(
                Transaction.account_id == account_id,
                Transaction.created_at >= cutoff_date,
                Transaction.plaid_transaction_id.isnot(None)
            ).order_by(Transaction.created_at.desc()).all()
            
            history = []
            import_dates = {}
            
            for transaction in imported_transactions:
                metadata = transaction.metadata_json or {}
                import_date = metadata.get('import_date', transaction.created_at.isoformat())
                
                # Group by import date
                if import_date not in import_dates:
                    import_dates[import_date] = {
                        'import_date': import_date,
                        'transaction_count': 0,
                        'total_amount': 0,
                        'transactions': []
                    }
                
                import_dates[import_date]['transaction_count'] += 1
                import_dates[import_date]['total_amount'] += transaction.amount_cents / 100
                import_dates[import_date]['transactions'].append({
                    'id': str(transaction.id),
                    'amount': transaction.amount_cents / 100,
                    'description': transaction.description,
                    'date': transaction.transaction_date.isoformat(),
                    'plaid_id': transaction.plaid_transaction_id
                })
            
            return list(import_dates.values())
            
        except Exception as e:
            logger.error(f"Failed to get import history for account {account_id}: {e}")
            raise

# Create global service instance
transaction_import_service = TransactionImportService()