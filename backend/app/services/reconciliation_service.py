"""
Account balance reconciliation service
Handles discrepancies between bank balances and calculated balances
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.account import AccountUpdate
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)

class ReconciliationService:
    """Service for account balance reconciliation and discrepancy detection"""
    
    def __init__(self):
        self.reconciliation_threshold = 0.01  # $0.01 tolerance
        
    def calculate_balance_from_transactions(self, db: Session, account_id: str) -> Dict[str, Any]:
        """Calculate account balance from transaction history"""
        try:
            # Get all transactions for this account
            transactions = db.query(Transaction).filter(
                Transaction.account_id == account_id,
                Transaction.status.in_(['posted', 'pending'])
            ).order_by(Transaction.transaction_date.asc()).all()
            
            if not transactions:
                return {
                    'calculated_balance_cents': 0,
                    'transaction_count': 0,
                    'earliest_transaction': None,
                    'latest_transaction': None
                }
            
            # Calculate running balance
            balance_cents = 0
            for transaction in transactions:
                # Positive amounts increase balance (income, refunds)
                # Negative amounts decrease balance (expenses, withdrawals)
                balance_cents += transaction.amount_cents
            
            return {
                'calculated_balance_cents': balance_cents,
                'transaction_count': len(transactions),
                'earliest_transaction': transactions[0].transaction_date.isoformat(),
                'latest_transaction': transactions[-1].transaction_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate balance for account {account_id}: {e}")
            raise
    
    def reconcile_account(self, db: Session, account_id: str) -> Dict[str, Any]:
        """Reconcile account balance with calculated balance from transactions"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            # Get calculated balance
            calculation = self.calculate_balance_from_transactions(db, account_id)
            calculated_balance_cents = calculation['calculated_balance_cents']
            
            # Get current recorded balance
            recorded_balance_cents = account.balance_cents
            
            # Calculate discrepancy
            discrepancy_cents = recorded_balance_cents - calculated_balance_cents
            discrepancy_amount = discrepancy_cents / 100
            
            # Determine reconciliation status
            is_reconciled = abs(discrepancy_cents) <= (self.reconciliation_threshold * 100)
            
            reconciliation_result = {
                'account_id': str(account.id),
                'account_name': account.name,
                'recorded_balance': recorded_balance_cents / 100,
                'calculated_balance': calculated_balance_cents / 100,
                'discrepancy': discrepancy_amount,
                'discrepancy_cents': discrepancy_cents,
                'is_reconciled': is_reconciled,
                'reconciliation_threshold': self.reconciliation_threshold,
                'transaction_count': calculation['transaction_count'],
                'reconciliation_date': datetime.utcnow().isoformat(),
                'suggestions': []
            }
            
            # Add suggestions based on discrepancy
            if not is_reconciled:
                reconciliation_result['suggestions'] = self._generate_reconciliation_suggestions(
                    discrepancy_cents, calculation
                )
            
            # Update account metadata with reconciliation info
            metadata = account.account_metadata or {}
            metadata['last_reconciliation'] = reconciliation_result
            account.account_metadata = metadata
            db.add(account)
            db.commit()
            
            logger.info(f"Reconciled account {account.name}: Discrepancy ${discrepancy_amount:.2f}")
            
            return reconciliation_result
            
        except Exception as e:
            logger.error(f"Failed to reconcile account {account_id}: {e}")
            raise
    
    def _generate_reconciliation_suggestions(
        self, 
        discrepancy_cents: int, 
        calculation: Dict[str, Any]
    ) -> List[str]:
        """Generate suggestions for resolving reconciliation discrepancies"""
        suggestions = []
        discrepancy_amount = discrepancy_cents / 100
        
        if discrepancy_cents > 0:
            # Recorded balance is higher than calculated
            suggestions.extend([
                f"Your recorded balance is ${abs(discrepancy_amount):.2f} higher than calculated from transactions",
                "This could be due to:",
                "• Missing income or deposit transactions",
                "• Pending transactions not yet recorded",
                "• Interest or fees not captured",
                "• Manual balance adjustments needed"
            ])
        else:
            # Recorded balance is lower than calculated
            suggestions.extend([
                f"Your recorded balance is ${abs(discrepancy_amount):.2f} lower than calculated from transactions",
                "This could be due to:",
                "• Missing expense or withdrawal transactions",
                "• Fees or charges not recorded",
                "• Transactions recorded with wrong amounts",
                "• Account balance needs to be updated from bank"
            ])
        
        # Add general suggestions
        suggestions.extend([
            "Recommended actions:",
            "• Sync with your bank for latest balance",
            "• Review recent transactions for accuracy",
            "• Check for pending or missing transactions",
            "• Consider manual reconciliation entry"
        ])
        
        return suggestions
    
    def reconcile_all_accounts(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Reconcile all accounts for a user"""
        try:
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).all()
            
            results = {
                'total_accounts': len(accounts),
                'reconciled_accounts': 0,
                'accounts_with_discrepancies': 0,
                'total_discrepancy': 0.0,
                'account_results': []
            }
            
            for account in accounts:
                try:
                    reconciliation = self.reconcile_account(db, str(account.id))
                    results['account_results'].append(reconciliation)
                    
                    if reconciliation['is_reconciled']:
                        results['reconciled_accounts'] += 1
                    else:
                        results['accounts_with_discrepancies'] += 1
                        results['total_discrepancy'] += abs(reconciliation['discrepancy'])
                        
                except Exception as e:
                    logger.error(f"Failed to reconcile account {account.id}: {e}")
                    results['account_results'].append({
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to reconcile accounts for user {user_id}: {e}")
            raise
    
    def create_reconciliation_entry(
        self, 
        db: Session, 
        account_id: str, 
        adjustment_cents: int, 
        description: str,
        user_id: str
    ) -> Transaction:
        """Create a reconciliation transaction to fix balance discrepancies"""
        try:
            from app.schemas.transaction import TransactionCreate
            from app.services.transaction_service import TransactionService
            
            transaction_service = TransactionService()
            
            # Create reconciliation transaction
            transaction_create = TransactionCreate(
                user_id=user_id,
                account_id=account_id,
                amount_cents=adjustment_cents,
                currency='USD',
                description=f"Balance Reconciliation: {description}",
                merchant="System Reconciliation",
                transaction_date=datetime.utcnow().date(),
                status='posted',
                notes="Automatic reconciliation adjustment",
                metadata_json={
                    'reconciliation': True,
                    'adjustment_type': 'balance_reconciliation',
                    'created_by': 'system',
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            transaction = transaction_service.create(db=db, obj_in=transaction_create)
            
            logger.info(f"Created reconciliation entry: ${adjustment_cents/100:.2f} for account {account_id}")
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to create reconciliation entry: {e}")
            raise
    
    def get_reconciliation_history(self, db: Session, account_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get reconciliation history for an account"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            # Get reconciliation entries from transaction metadata
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            reconciliation_transactions = db.query(Transaction).filter(
                Transaction.account_id == account_id,
                Transaction.created_at >= cutoff_date,
                Transaction.metadata_json.op('->>')('reconciliation').cast(db.TEXT) == 'true'
            ).order_by(Transaction.created_at.desc()).all()
            
            history = []
            for transaction in reconciliation_transactions:
                metadata = transaction.metadata_json or {}
                
                history.append({
                    'transaction_id': str(transaction.id),
                    'date': transaction.transaction_date.isoformat(),
                    'adjustment_amount': transaction.amount_cents / 100,
                    'description': transaction.description,
                    'adjustment_type': metadata.get('adjustment_type', 'manual'),
                    'created_by': metadata.get('created_by', 'user'),
                    'timestamp': metadata.get('timestamp', transaction.created_at.isoformat())
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get reconciliation history for account {account_id}: {e}")
            raise
    
    def schedule_daily_reconciliation(self, db: Session) -> Dict[str, Any]:
        """Schedule daily reconciliation for all active accounts with Plaid connections"""
        try:
            # Get all accounts that need reconciliation
            accounts_to_reconcile = db.query(Account).filter(
                Account.is_active == True,
                Account.plaid_access_token.isnot(None)
            ).all()
            
            results = {
                'scheduled_accounts': len(accounts_to_reconcile),
                'reconciliation_time': datetime.utcnow().isoformat(),
                'accounts': []
            }
            
            for account in accounts_to_reconcile:
                # Update metadata to mark for reconciliation
                metadata = account.account_metadata or {}
                metadata['reconciliation_scheduled'] = True
                metadata['next_reconciliation'] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
                account.account_metadata = metadata
                
                results['accounts'].append({
                    'account_id': str(account.id),
                    'name': account.name,
                    'scheduled_time': metadata['next_reconciliation']
                })
            
            db.commit()
            
            logger.info(f"Scheduled reconciliation for {len(accounts_to_reconcile)} accounts")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to schedule daily reconciliation: {e}")
            raise

# Create global service instance
reconciliation_service = ReconciliationService()