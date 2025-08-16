"""
Enhanced Account Reconciliation Service
Advanced reconciliation with smart discrepancy detection and resolution
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate
from app.services.transaction_service import TransactionService
from app.websocket.manager import redis_websocket_manager as websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)

@dataclass
class ReconciliationResult:
    """Result of account reconciliation"""
    account_id: str
    account_name: str
    is_reconciled: bool
    expected_balance_cents: int
    actual_balance_cents: int
    discrepancy_cents: int
    discrepancy_type: str  # 'none', 'positive', 'negative'
    transaction_count: int
    reconciliation_date: datetime
    suggestions: List[str]
    confidence_score: float  # 0-100
    details: Dict[str, Any]
    
    @property
    def expected_balance(self) -> float:
        """Convert cents to dollars for display"""
        return self.expected_balance_cents / 100.0
    
    @property
    def actual_balance(self) -> float:
        """Convert cents to dollars for display"""
        return self.actual_balance_cents / 100.0
    
    @property
    def discrepancy(self) -> float:
        """Convert cents to dollars for display"""
        return self.discrepancy_cents / 100.0

@dataclass
class TransactionMatch:
    """Matching transaction for reconciliation"""
    plaid_transaction: Dict[str, Any]
    existing_transaction: Optional[Transaction]
    match_confidence: float
    match_type: str  # 'exact', 'fuzzy', 'partial', 'none'

class EnhancedReconciliationService:
    """Enhanced reconciliation service with intelligent discrepancy detection"""
    
    def __init__(self):
        self.transaction_service = TransactionService()
        
        # Reconciliation configuration
        self.tolerance_cents = 1  # 1 cent tolerance for floating point errors
        self.confidence_threshold = 0.85
        self.max_days_for_analysis = 90
        
        # Matching parameters
        self.match_thresholds = {
            'exact_match': 1.0,
            'high_confidence': 0.9,
            'medium_confidence': 0.7,
            'low_confidence': 0.5
        }
    
    async def reconcile_account(self, db: Session, account_id: str) -> ReconciliationResult:
        """Perform comprehensive account reconciliation"""
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")
        
        # Get all transactions for this account
        transactions = db.query(Transaction).filter(
            Transaction.account_id == account_id
        ).all()
        
        # Calculate expected balance from transactions (keep as cents)
        expected_balance_cents = sum(txn.amount_cents for txn in transactions)
        actual_balance_cents = account.balance_cents
        
        # Calculate discrepancy in cents (integer arithmetic only)
        discrepancy_cents = actual_balance_cents - expected_balance_cents
        
        # Determine if reconciled (within tolerance)
        is_reconciled = abs(discrepancy_cents) <= self.tolerance_cents
        
        # Analyze discrepancy
        analysis = await self._analyze_discrepancy(
            account, transactions, discrepancy_cents, db
        )
        
        # Generate suggestions
        suggestions = await self._generate_reconciliation_suggestions(
            account, discrepancy_cents, analysis, db
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            account, transactions, discrepancy_cents, analysis
        )
        
        result = ReconciliationResult(
            account_id=str(account.id),
            account_name=account.name,
            is_reconciled=is_reconciled,
            expected_balance_cents=expected_balance_cents,
            actual_balance_cents=actual_balance_cents,
            discrepancy_cents=discrepancy_cents,
            discrepancy_type=self._categorize_discrepancy(discrepancy_cents),
            transaction_count=len(transactions),
            reconciliation_date=datetime.now(timezone.utc),
            suggestions=suggestions,
            confidence_score=confidence_score,
            details=analysis
        )
        
        # Update account reconciliation metadata
        await self._update_account_reconciliation_metadata(account, result, db)
        
        return result
    
    async def reconcile_with_plaid_data(
        self, 
        db: Session, 
        account_id: str,
        plaid_transactions: List[Dict[str, Any]],
        plaid_balance: float
    ) -> Dict[str, Any]:
        """Reconcile account using fresh Plaid data"""
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")
        
        # Get existing transactions
        existing_transactions = db.query(Transaction).filter(
            Transaction.account_id == account_id
        ).all()
        
        # Match Plaid transactions with existing ones
        matches = await self._match_transactions(plaid_transactions, existing_transactions)
        
        # Identify discrepancies
        discrepancies = await self._identify_transaction_discrepancies(matches)
        
        # Calculate balance discrepancy in cents
        plaid_balance_cents = int(plaid_balance * 100)
        balance_discrepancy_cents = plaid_balance_cents - account.balance_cents
        
        # Generate reconciliation report
        report = {
            'account_id': str(account.id),
            'account_name': account.name,
            'plaid_balance': plaid_balance,
            'current_balance': account.balance_cents / 100.0,
            'balance_discrepancy': balance_discrepancy_cents / 100.0,
            'transaction_matches': {
                'total_plaid_transactions': len(plaid_transactions),
                'total_existing_transactions': len(existing_transactions),
                'exact_matches': len([m for m in matches if m.match_type == 'exact']),
                'fuzzy_matches': len([m for m in matches if m.match_type == 'fuzzy']),
                'unmatched_plaid': len([m for m in matches if m.match_type == 'none' and m.plaid_transaction]),
                'unmatched_existing': len([m for m in matches if m.match_type == 'none' and m.existing_transaction])
            },
            'discrepancies': discrepancies,
            'recommendations': await self._generate_plaid_reconciliation_recommendations(
                matches, balance_discrepancy_cents, discrepancies
            )
        }
        
        return report
    
    async def _analyze_discrepancy(
        self, 
        account: Account, 
        transactions: List[Transaction], 
        discrepancy_cents: int, 
        db: Session
    ) -> Dict[str, Any]:
        """Analyze the source of balance discrepancy"""
        
        analysis = {
            'total_transactions': len(transactions),
            'transaction_sum_cents': sum(txn.amount_cents for txn in transactions),
            'transaction_sum': sum(txn.amount_cents for txn in transactions) / 100.0,
            'date_range': self._get_transaction_date_range(transactions),
            'potential_causes': [],
            'missing_transactions': 0,
            'duplicate_transactions': 0,
            'pending_transactions': 0,
            'reconciliation_entries': 0
        }
        
        if not transactions:
            analysis['potential_causes'].append('No transactions found for this account')
            return analysis
        
        # Check for pending transactions
        pending_txns = [txn for txn in transactions if txn.status == 'pending']
        analysis['pending_transactions'] = len(pending_txns)
        if pending_txns:
            analysis['potential_causes'].append(f'{len(pending_txns)} pending transactions may not be reflected in balance')
        
        # Check for recent reconciliation entries
        reconciliation_txns = [
            txn for txn in transactions 
            if 'reconciliation' in (txn.description or '').lower()
        ]
        analysis['reconciliation_entries'] = len(reconciliation_txns)
        
        # Look for potential duplicate transactions
        duplicates = await self._find_potential_duplicates(transactions)
        analysis['duplicate_transactions'] = len(duplicates)
        if duplicates:
            analysis['potential_causes'].append(f'{len(duplicates)} potential duplicate transactions found')
        
        # Check for missing recent transactions (if Plaid connected)
        if account.is_plaid_connected:
            missing_estimate = await self._estimate_missing_transactions(account, db)
            analysis['missing_transactions'] = missing_estimate
            if missing_estimate > 0:
                analysis['potential_causes'].append(f'Approximately {missing_estimate} transactions may be missing')
        
        # Analyze transaction patterns
        pattern_analysis = await self._analyze_transaction_patterns(transactions)
        analysis.update(pattern_analysis)
        
        return analysis
    
    async def _match_transactions(
        self, 
        plaid_transactions: List[Dict[str, Any]], 
        existing_transactions: List[Transaction]
    ) -> List[TransactionMatch]:
        """Match Plaid transactions with existing database transactions"""
        
        matches = []
        used_existing = set()
        
        for plaid_txn in plaid_transactions:
            best_match = None
            best_confidence = 0
            
            # First try exact matching by Plaid ID
            plaid_id = plaid_txn.get('transaction_id')
            if plaid_id:
                for existing_txn in existing_transactions:
                    if existing_txn.plaid_transaction_id == plaid_id:
                        best_match = existing_txn
                        best_confidence = 1.0
                        break
            
            # If no exact match, try fuzzy matching
            if not best_match:
                for existing_txn in existing_transactions:
                    if existing_txn.id in used_existing:
                        continue
                    
                    confidence = self._calculate_match_confidence(plaid_txn, existing_txn)
                    if confidence > best_confidence and confidence >= self.match_thresholds['low_confidence']:
                        best_match = existing_txn
                        best_confidence = confidence
            
            # Determine match type
            if best_confidence >= self.match_thresholds['exact_match']:
                match_type = 'exact'
            elif best_confidence >= self.match_thresholds['high_confidence']:
                match_type = 'fuzzy'
            elif best_confidence >= self.match_thresholds['medium_confidence']:
                match_type = 'partial'
            else:
                match_type = 'none'
                best_match = None
            
            matches.append(TransactionMatch(
                plaid_transaction=plaid_txn,
                existing_transaction=best_match,
                match_confidence=best_confidence,
                match_type=match_type
            ))
            
            if best_match:
                used_existing.add(best_match.id)
        
        # Add unmatched existing transactions
        for existing_txn in existing_transactions:
            if existing_txn.id not in used_existing:
                matches.append(TransactionMatch(
                    plaid_transaction=None,
                    existing_transaction=existing_txn,
                    match_confidence=0,
                    match_type='none'
                ))
        
        return matches
    
    def _calculate_match_confidence(self, plaid_txn: Dict[str, Any], existing_txn: Transaction) -> float:
        """Calculate confidence score for transaction matching"""
        
        score = 0.0
        
        # Amount matching (most important) - use integer cents for precision
        plaid_amount_cents = int(float(plaid_txn.get('amount', 0)) * 100)
        existing_amount_cents = existing_txn.amount_cents
        
        # Plaid amounts are positive for debits, we store negative for expenses
        amount_diff_cents = abs(abs(plaid_amount_cents) - abs(existing_amount_cents))
        if amount_diff_cents <= 1:  # Within 1 cent
            score += 0.4
        elif amount_diff_cents <= 100:  # Within $1.00
            score += 0.2
        
        # Date matching
        plaid_date = plaid_txn.get('date')
        if plaid_date and existing_txn.transaction_date:
            try:
                plaid_dt = datetime.fromisoformat(plaid_date).date()
                existing_dt = existing_txn.transaction_date.date()
                
                date_diff = abs((plaid_dt - existing_dt).days)
                if date_diff == 0:
                    score += 0.3
                elif date_diff <= 2:
                    score += 0.15
                elif date_diff <= 7:
                    score += 0.05
            except:
                pass
        
        # Description matching
        plaid_desc = (plaid_txn.get('name', '') or '').lower()
        existing_desc = (existing_txn.description or '').lower()
        
        if plaid_desc and existing_desc:
            # Simple fuzzy matching
            common_words = set(plaid_desc.split()) & set(existing_desc.split())
            if common_words:
                desc_score = len(common_words) / max(len(plaid_desc.split()), len(existing_desc.split()))
                score += desc_score * 0.2
        
        # Merchant matching
        plaid_merchant = plaid_txn.get('merchant_name', '').lower()
        existing_merchant = (existing_txn.merchant or '').lower()
        
        if plaid_merchant and existing_merchant:
            if plaid_merchant == existing_merchant:
                score += 0.1
            elif plaid_merchant in existing_merchant or existing_merchant in plaid_merchant:
                score += 0.05
        
        return min(1.0, score)
    
    async def _identify_transaction_discrepancies(
        self, 
        matches: List[TransactionMatch]
    ) -> List[Dict[str, Any]]:
        """Identify transaction discrepancies from matches"""
        
        discrepancies = []
        
        for match in matches:
            if match.match_type == 'none':
                if match.plaid_transaction and not match.existing_transaction:
                    discrepancies.append({
                        'type': 'missing_transaction',
                        'description': 'Transaction exists in Plaid but not in database',
                        'plaid_transaction': match.plaid_transaction,
                        'amount': match.plaid_transaction.get('amount', 0),
                        'date': match.plaid_transaction.get('date'),
                        'name': match.plaid_transaction.get('name')
                    })
                elif match.existing_transaction and not match.plaid_transaction:
                    discrepancies.append({
                        'type': 'extra_transaction',
                        'description': 'Transaction exists in database but not in Plaid',
                        'existing_transaction_id': str(match.existing_transaction.id),
                        'amount_cents': match.existing_transaction.amount_cents,
                        'amount': match.existing_transaction.amount_cents / 100.0,
                        'date': match.existing_transaction.transaction_date.isoformat() if match.existing_transaction.transaction_date else None,
                        'description': match.existing_transaction.description
                    })
            
            elif match.match_type in ['fuzzy', 'partial']:
                # Check for amount discrepancies in matched transactions
                if match.plaid_transaction and match.existing_transaction:
                    plaid_amount_cents = int(float(match.plaid_transaction.get('amount', 0)) * 100)
                    existing_amount_cents = match.existing_transaction.amount_cents
                    
                    # Check discrepancy using integer cents (1 cent tolerance)
                    if abs(abs(plaid_amount_cents) - abs(existing_amount_cents)) > 1:
                        discrepancies.append({
                            'type': 'amount_mismatch',
                            'description': 'Transaction amounts do not match',
                            'plaid_amount_cents': plaid_amount_cents,
                            'existing_amount_cents': existing_amount_cents,
                            'plaid_amount': plaid_amount_cents / 100.0,
                            'existing_amount': existing_amount_cents / 100.0,
                            'difference_cents': abs(plaid_amount_cents) - abs(existing_amount_cents),
                            'difference': (abs(plaid_amount_cents) - abs(existing_amount_cents)) / 100.0,
                            'match_confidence': match.match_confidence
                        })
        
        return discrepancies
    
    async def _find_potential_duplicates(self, transactions: List[Transaction]) -> List[Tuple[Transaction, Transaction]]:
        """Find potential duplicate transactions"""
        
        duplicates = []
        
        for i, txn1 in enumerate(transactions):
            for j, txn2 in enumerate(transactions[i+1:], i+1):
                if self._are_potentially_duplicate(txn1, txn2):
                    duplicates.append((txn1, txn2))
        
        return duplicates
    
    def _are_potentially_duplicate(self, txn1: Transaction, txn2: Transaction) -> bool:
        """Check if two transactions are potentially duplicates"""
        
        # Same amount
        if txn1.amount_cents != txn2.amount_cents:
            return False
        
        # Similar dates (within 3 days)
        if txn1.transaction_date and txn2.transaction_date:
            date_diff = abs((txn1.transaction_date.date() - txn2.transaction_date.date()).days)
            if date_diff > 3:
                return False
        
        # Similar descriptions
        desc1 = (txn1.description or '').lower()
        desc2 = (txn2.description or '').lower()
        
        if desc1 and desc2:
            # Simple similarity check
            common_words = set(desc1.split()) & set(desc2.split())
            if len(common_words) >= min(2, len(desc1.split()) * 0.5):
                return True
        
        return False
    
    async def _estimate_missing_transactions(self, account: Account, db: Session) -> int:
        """Estimate number of missing transactions for Plaid-connected account"""
        
        if not account.last_sync_at:
            return 0
        
        # Look at transaction frequency in recent history
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_transactions = db.query(Transaction).filter(
            Transaction.account_id == account.id,
            Transaction.transaction_date >= recent_cutoff
        ).count()
        
        # Calculate average transactions per day
        if recent_transactions > 0:
            days_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).days
            avg_per_day = recent_transactions / 30
            expected_since_sync = int(avg_per_day * days_since_sync)
            
            # This is a rough estimate
            return max(0, expected_since_sync - 5)  # Buffer for estimation error
        
        return 0
    
    async def _analyze_transaction_patterns(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze transaction patterns for insights"""
        
        if not transactions:
            return {}
        
        # Group by month
        monthly_counts = {}
        monthly_amounts_cents = {}
        monthly_amounts = {}
        
        for txn in transactions:
            if txn.transaction_date:
                month_key = txn.transaction_date.strftime('%Y-%m')
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
                monthly_amounts_cents[month_key] = monthly_amounts_cents.get(month_key, 0) + txn.amount_cents
                monthly_amounts[month_key] = monthly_amounts_cents[month_key] / 100.0
        
        # Calculate averages
        if monthly_counts:
            avg_monthly_transactions = sum(monthly_counts.values()) / len(monthly_counts)
            avg_monthly_amount_cents = sum(monthly_amounts_cents.values()) // len(monthly_amounts_cents)
            avg_monthly_amount = avg_monthly_amount_cents / 100.0
        else:
            avg_monthly_transactions = 0
            avg_monthly_amount_cents = 0
            avg_monthly_amount = 0
        
        return {
            'monthly_transaction_counts': monthly_counts,
            'monthly_amounts_cents': monthly_amounts_cents,
            'monthly_amounts': monthly_amounts,
            'avg_monthly_transactions': avg_monthly_transactions,
            'avg_monthly_amount_cents': avg_monthly_amount_cents,
            'avg_monthly_amount': avg_monthly_amount,
            'total_months_analyzed': len(monthly_counts)
        }
    
    def _get_transaction_date_range(self, transactions: List[Transaction]) -> Dict[str, Optional[str]]:
        """Get the date range of transactions"""
        
        dates = [txn.transaction_date for txn in transactions if txn.transaction_date]
        
        if not dates:
            return {'earliest': None, 'latest': None}
        
        return {
            'earliest': min(dates).isoformat(),
            'latest': max(dates).isoformat()
        }
    
    async def _generate_reconciliation_suggestions(
        self, 
        account: Account, 
        discrepancy_cents: int, 
        analysis: Dict[str, Any], 
        db: Session
    ) -> List[str]:
        """Generate actionable reconciliation suggestions"""
        
        suggestions = []
        
        if abs(discrepancy_cents) <= 1:  # Reconciled within 1 cent
            suggestions.append("Account is properly reconciled")
            return suggestions
        
        # Discrepancy-specific suggestions
        discrepancy_dollars = discrepancy_cents / 100.0
        if discrepancy_cents > 0:
            suggestions.append(f"Account balance is ${abs(discrepancy_dollars):.2f} higher than expected")
            suggestions.append("Check for missing expense transactions or extra income")
        else:
            suggestions.append(f"Account balance is ${abs(discrepancy_dollars):.2f} lower than expected")
            suggestions.append("Check for missing income transactions or extra expenses")
        
        # Analysis-based suggestions
        if analysis.get('pending_transactions', 0) > 0:
            suggestions.append(f"Consider {analysis['pending_transactions']} pending transactions that may not be reflected in balance")
        
        if analysis.get('duplicate_transactions', 0) > 0:
            suggestions.append(f"Review {analysis['duplicate_transactions']} potential duplicate transactions")
        
        if analysis.get('missing_transactions', 0) > 0:
            suggestions.append(f"Sync account to import approximately {analysis['missing_transactions']} missing transactions")
        
        if account.is_plaid_connected and account.last_sync_at:
            hours_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).total_seconds() / 3600
            if hours_since_sync > 24:
                suggestions.append("Sync account with your bank to get latest transactions")
        
        # Large discrepancy suggestions (over $100)
        if abs(discrepancy_cents) > 10000:  # 10000 cents = $100
            suggestions.append("Large discrepancy detected - consider manual reconciliation entry")
        
        return suggestions[:5]  # Return top 5 suggestions
    
    async def _generate_plaid_reconciliation_recommendations(
        self, 
        matches: List[TransactionMatch], 
        balance_discrepancy_cents: int, 
        discrepancies: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on Plaid reconciliation"""
        
        recommendations = []
        
        # Missing transactions
        missing_count = len([d for d in discrepancies if d['type'] == 'missing_transaction'])
        if missing_count > 0:
            recommendations.append(f"Import {missing_count} missing transactions from Plaid")
        
        # Extra transactions
        extra_count = len([d for d in discrepancies if d['type'] == 'extra_transaction'])
        if extra_count > 0:
            recommendations.append(f"Review {extra_count} transactions that may be duplicates or errors")
        
        # Amount mismatches
        mismatch_count = len([d for d in discrepancies if d['type'] == 'amount_mismatch'])
        if mismatch_count > 0:
            recommendations.append(f"Correct {mismatch_count} transactions with amount discrepancies")
        
        # Balance discrepancy
        if abs(balance_discrepancy_cents) > 1:  # More than 1 cent
            balance_discrepancy_dollars = balance_discrepancy_cents / 100.0
            if balance_discrepancy_cents > 0:
                recommendations.append(f"Account balance is ${balance_discrepancy_dollars:.2f} higher than Plaid balance")
            else:
                recommendations.append(f"Account balance is ${abs(balance_discrepancy_dollars):.2f} lower than Plaid balance")
        
        if not recommendations:
            recommendations.append("Account is in sync with Plaid data")
        
        return recommendations
    
    def _calculate_confidence_score(
        self, 
        account: Account, 
        transactions: List[Transaction], 
        discrepancy_cents: int, 
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for reconciliation"""
        
        score = 100.0
        
        # Deduct for discrepancy size (penalty based on dollars)
        discrepancy_dollars = abs(discrepancy_cents) / 100.0
        discrepancy_penalty = min(50, discrepancy_dollars * 2)
        score -= discrepancy_penalty
        
        # Deduct for potential issues
        if analysis.get('duplicate_transactions', 0) > 0:
            score -= min(20, analysis['duplicate_transactions'] * 5)
        
        if analysis.get('missing_transactions', 0) > 0:
            score -= min(30, analysis['missing_transactions'] * 2)
        
        # Deduct for stale data
        if account.is_plaid_connected and account.last_sync_at:
            hours_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).total_seconds() / 3600
            if hours_since_sync > 168:  # 1 week
                score -= 25
            elif hours_since_sync > 48:  # 2 days
                score -= 10
        
        return max(0, min(100, score))
    
    def _categorize_discrepancy(self, discrepancy_cents: int) -> str:
        """Categorize discrepancy type"""
        if abs(discrepancy_cents) <= 1:  # Within 1 cent
            return 'none'
        elif discrepancy_cents > 0:
            return 'positive'
        else:
            return 'negative'
    
    async def _update_account_reconciliation_metadata(
        self, 
        account: Account, 
        result: ReconciliationResult, 
        db: Session
    ):
        """Update account with reconciliation metadata"""
        
        metadata = account.account_metadata or {}
        
        # Add reconciliation history
        reconciliation_entry = {
            'timestamp': result.reconciliation_date.isoformat(),
            'is_reconciled': result.is_reconciled,
            'discrepancy_cents': result.discrepancy_cents,
            'discrepancy': result.discrepancy,  # Keep for backward compatibility
            'confidence_score': result.confidence_score,
            'transaction_count': result.transaction_count
        }
        
        if 'reconciliation_history' not in metadata:
            metadata['reconciliation_history'] = []
        
        metadata['reconciliation_history'].append(reconciliation_entry)
        
        # Keep only last 20 reconciliation records
        metadata['reconciliation_history'] = metadata['reconciliation_history'][-20:]
        
        # Update latest reconciliation info
        metadata['last_reconciliation'] = reconciliation_entry
        
        account.account_metadata = metadata
        db.add(account)
        db.commit()
    
    async def create_reconciliation_entry(
        self, 
        db: Session, 
        account_id: str, 
        adjustment_cents: int, 
        description: str, 
        user_id: str
    ) -> Transaction:
        """Create a manual reconciliation entry to fix balance discrepancy"""
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")
        
        transaction_create = TransactionCreate(
            user_id=user_id,
            account_id=account_id,
            amount_cents=adjustment_cents,
            currency=account.currency,
            description=f"Reconciliation Adjustment: {description}",
            transaction_date=datetime.now(timezone.utc),
            status='posted',
            metadata_json={
                'type': 'reconciliation_entry',
                'created_by': 'manual_reconciliation',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        
        transaction = self.transaction_service.create(db=db, obj_in=transaction_create)
        
        # Update account balance if this is a real adjustment
        account.balance_cents += adjustment_cents
        db.add(account)
        db.commit()
        
        logger.info(f"Created reconciliation entry for account {account.name}: ${adjustment_cents/100:.2f}")
        
        return transaction
    
    async def reconcile_all_accounts(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Reconcile all accounts for a user"""
        
        accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        if not accounts:
            return {
                'total_accounts': 0,
                'reconciled_accounts': 0,
                'accounts_with_discrepancies': 0,
                'total_discrepancy': 0,
                'results': []
            }
        
        results = []
        total_discrepancy = 0
        reconciled_count = 0
        discrepancy_count = 0
        
        for account in accounts:
            try:
                result = await self.reconcile_account(db, str(account.id))
                results.append({
                    'account_id': result.account_id,
                    'account_name': result.account_name,
                    'is_reconciled': result.is_reconciled,
                    'discrepancy': result.discrepancy,
                    'confidence_score': result.confidence_score
                })
                
                if result.is_reconciled:
                    reconciled_count += 1
                else:
                    discrepancy_count += 1
                    total_discrepancy += abs(result.discrepancy)
                    
            except Exception as e:
                logger.error(f"Failed to reconcile account {account.id}: {e}")
                results.append({
                    'account_id': str(account.id),
                    'account_name': account.name,
                    'is_reconciled': False,
                    'discrepancy': 0,
                    'error': str(e)
                })
        
        return {
            'total_accounts': len(accounts),
            'reconciled_accounts': reconciled_count,
            'accounts_with_discrepancies': discrepancy_count,
            'total_discrepancy': total_discrepancy,
            'results': results
        }
    
    async def get_reconciliation_history(
        self, 
        db: Session, 
        account_id: str, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get reconciliation history for an account"""
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")
        
        metadata = account.account_metadata or {}
        reconciliation_history = metadata.get('reconciliation_history', [])
        
        # Filter by date range if specified
        if days and days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            filtered_history = []
            
            for entry in reconciliation_history:
                try:
                    entry_date = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if entry_date >= cutoff_date:
                        filtered_history.append(entry)
                except:
                    # Include entries with invalid dates
                    filtered_history.append(entry)
            
            reconciliation_history = filtered_history
        
        # Sort by timestamp (newest first)
        try:
            reconciliation_history.sort(
                key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')),
                reverse=True
            )
        except:
            pass
        
        return reconciliation_history

# Global service instance
enhanced_reconciliation_service = EnhancedReconciliationService()