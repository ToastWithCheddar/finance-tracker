"""
Financial Health Service
Handles financial health calculations, scoring, and analysis
Extracted from AccountInsightsService for better separation of concerns
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.financial_health_config import FinancialHealthConfig, DEFAULT_FINANCIAL_HEALTH_CONFIG
from app.schemas.account_health import AccountHealthData, ReconciliationHealth, ConnectionHealth

logger = logging.getLogger(__name__)


class FinancialHealthService:
    """Service for calculating financial health metrics and scores"""
    
    def __init__(self, config: Optional[FinancialHealthConfig] = None):
        """Initialize with optional configuration override"""
        self.config = config or DEFAULT_FINANCIAL_HEALTH_CONFIG
        logger.debug(f"FinancialHealthService initialized with config: {self.config.dict()}")
    
    def calculate_account_health_score(
        self, 
        account: Account, 
        transaction_count: int, 
        activity_level: str, 
        total_income: int, 
        total_expenses: int
    ) -> int:
        """Calculate health score (0-100) for an individual account"""
        score = self.config.scoring.base_score
        balance = account.balance_cents
        
        logger.debug(f"Calculating account health for account {account.id}: balance={balance}, activity={activity_level}")
        
        # Balance health (40% weight)
        if balance < 0:  # Negative balance
            penalty = self.config.balance.negative_penalty
            score -= penalty
            logger.debug(f"Applied negative balance penalty: -{penalty}")
        elif balance < self.config.balance.low_balance_threshold:  
            penalty = self.config.balance.low_balance_penalty
            score -= penalty
            logger.debug(f"Applied low balance penalty: -{penalty} (threshold: {self.config.balance.low_balance_threshold})")
        elif balance > self.config.balance.good_balance_threshold:  
            bonus = self.config.balance.good_balance_bonus
            score += bonus
            logger.debug(f"Applied good balance bonus: +{bonus} (threshold: {self.config.balance.good_balance_threshold})")
        
        # Activity health (30% weight)
        if activity_level == 'inactive':
            penalty = self.config.activity.inactive_penalty
            score -= penalty
            logger.debug(f"Applied inactive account penalty: -{penalty}")
        elif activity_level == 'high':
            bonus = self.config.activity.high_activity_bonus
            score += bonus
            logger.debug(f"Applied high activity bonus: +{bonus}")
        
        # Cash flow health (30% weight)
        if total_income > 0 and total_expenses > 0:
            net_flow = total_income - abs(total_expenses)
            if net_flow > 0:
                bonus = self.config.cash_flow.positive_flow_bonus
                score += bonus
                logger.debug(f"Applied positive cash flow bonus: +{bonus}")
            elif net_flow < -self.config.cash_flow.high_spending_threshold:
                penalty = self.config.cash_flow.high_spending_penalty
                score -= penalty
                logger.debug(f"Applied high spending penalty: -{penalty} (threshold: {self.config.cash_flow.high_spending_threshold})")
        
        # Connection health bonus
        if account.plaid_access_token:
            metadata = account.account_metadata or {}
            last_sync = metadata.get('last_sync')
            if last_sync:
                try:
                    last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', ''))
                    hours_since_sync = (datetime.utcnow() - last_sync_dt).total_seconds() / 3600
                    if hours_since_sync < self.config.activity.sync_hours_threshold:
                        bonus = self.config.activity.sync_bonus
                        score += bonus
                        logger.debug(f"Applied recent sync bonus: +{bonus} (hours since sync: {hours_since_sync:.1f})")
                except (ValueError, TypeError):
                    # Invalid date format, skip sync bonus
                    logger.debug("Invalid sync date format, skipping sync bonus")
                    pass
        
        final_score = max(self.config.scoring.min_score, min(self.config.scoring.max_score, score))
        logger.debug(f"Final account health score: {final_score}")
        return final_score
    
    def calculate_overall_financial_health(self, categorization: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall financial health metrics from account categorization"""
        try:
            categories = categorization['categories']
            
            # Calculate totals
            total_liquid = sum(
                account['balance'] for account in categories['spending'] + categories['saving']
                if account['balance'] > 0
            )
            
            total_debt = sum(
                abs(account['balance']) for account in categories['credit']
                if account['balance'] < 0
            )
            
            total_investment = sum(
                account['balance'] for account in categories['investment']
                if account['balance'] > 0
            )
            
            net_worth = total_liquid + total_investment - total_debt
            
            # Calculate ratios
            debt_ratio = total_debt / max(1, total_liquid) if total_liquid > 0 else 0
            investment_ratio = total_investment / max(1, total_liquid + total_investment) if total_liquid + total_investment > 0 else 0
            
            # Determine overall health score
            health_score = self.config.scoring.base_score
            
            logger.debug(f"Calculating overall financial health: debt_ratio={debt_ratio:.3f}, investment_ratio={investment_ratio:.3f}, net_worth={net_worth}")
            
            # Debt ratio penalties
            if debt_ratio > self.config.debt.high_debt_ratio:
                penalty = self.config.debt.high_debt_penalty
                health_score -= penalty
                logger.debug(f"Applied high debt ratio penalty: -{penalty} (ratio: {debt_ratio:.3f})")
            elif debt_ratio > self.config.debt.moderate_debt_ratio:
                penalty = self.config.debt.moderate_debt_penalty
                health_score -= penalty
                logger.debug(f"Applied moderate debt ratio penalty: -{penalty} (ratio: {debt_ratio:.3f})")
            
            # Investment ratio adjustments
            if investment_ratio < self.config.investment.min_investment_ratio and total_liquid > self.config.investment.min_liquid_for_investment:
                penalty = self.config.investment.low_investment_penalty
                health_score -= penalty
                logger.debug(f"Applied low investment penalty: -{penalty} (ratio: {investment_ratio:.3f}, liquid: {total_liquid})")
            elif investment_ratio > self.config.investment.good_investment_ratio:
                bonus = self.config.investment.good_investment_bonus
                health_score += bonus
                logger.debug(f"Applied good investment bonus: +{bonus} (ratio: {investment_ratio:.3f})")
            
            # Net worth adjustments
            if net_worth < 0:
                penalty = self.config.net_worth.negative_net_worth_penalty
                health_score -= penalty
                logger.debug(f"Applied negative net worth penalty: -{penalty}")
            elif net_worth > self.config.net_worth.good_net_worth_threshold:
                bonus = self.config.net_worth.good_net_worth_bonus
                health_score += bonus
                logger.debug(f"Applied good net worth bonus: +{bonus} (net worth: {net_worth})")
            
            # Health grade
            grade = self._calculate_health_grade(health_score)
            
            final_score = max(self.config.scoring.min_score, min(self.config.scoring.max_score, health_score))
            logger.debug(f"Final overall health score: {final_score}, grade: {grade}")
            
            return {
                'overall_score': final_score,
                'grade': grade,
                'net_worth': net_worth,
                'total_liquid': total_liquid,
                'total_debt': total_debt,
                'total_investment': total_investment,
                'debt_ratio': debt_ratio,
                'investment_ratio': investment_ratio,
                'account_diversity': len([cat for cat in categories.values() if len(cat) > 0]),
                'recommendations': self._generate_health_recommendations(
                    final_score, debt_ratio, investment_ratio, net_worth, total_liquid
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate financial health: {e}")
            return {
                'overall_score': 0,
                'grade': 'F',
                'error': str(e),
                'recommendations': ['Unable to calculate financial health due to data error']
            }
    
    def calculate_user_financial_health(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Calculate comprehensive financial health for a user"""
        try:
            # Get all user accounts
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).all()
            
            if not accounts:
                return {
                    'overall_score': 0,
                    'grade': 'N/A',
                    'message': 'No active accounts found',
                    'recommendations': ['Connect your bank accounts to get started with financial health tracking']
                }
            
            # Calculate basic metrics
            total_balance = sum(account.balance_cents for account in accounts) / 100
            account_count = len(accounts)
            
            # Get recent transaction activity
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_transactions = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= thirty_days_ago.date()
            ).count()
            
            # Simple categorization for health calculation
            liquid_accounts = []
            debt_accounts = []
            investment_accounts = []
            
            for account in accounts:
                if account.account_type in ['checking', 'savings']:
                    liquid_accounts.append({
                        'balance': account.balance_cents / 100,
                        'type': account.account_type
                    })
                elif account.account_type in ['credit_card']:
                    debt_accounts.append({
                        'balance': account.balance_cents / 100,
                        'type': account.account_type
                    })
                elif account.account_type in ['investment', 'retirement']:
                    investment_accounts.append({
                        'balance': account.balance_cents / 100,
                        'type': account.account_type
                    })
            
            # Calculate health metrics
            total_liquid = sum(acc['balance'] for acc in liquid_accounts if acc['balance'] > 0)
            total_debt = sum(abs(acc['balance']) for acc in debt_accounts if acc['balance'] < 0)
            total_investment = sum(acc['balance'] for acc in investment_accounts if acc['balance'] > 0)
            
            net_worth = total_liquid + total_investment - total_debt
            
            # Calculate ratios
            debt_ratio = total_debt / max(1, total_liquid) if total_liquid > 0 else 0
            investment_ratio = total_investment / max(1, total_liquid + total_investment) if total_liquid + total_investment > 0 else 0
            
            # Base health score
            health_score = self.config.scoring.user_base_score
            
            logger.debug(f"Calculating user financial health: balance={total_balance}, debt_ratio={debt_ratio:.3f}, investment_ratio={investment_ratio:.3f}")
            
            # Balance factors
            if total_balance > 0:
                bonus = self.config.user_health.positive_balance_bonus
                health_score += bonus
                logger.debug(f"Applied positive balance bonus: +{bonus}")
            if total_balance > self.config.user_health.high_balance_threshold / 100:  # Convert cents to dollars
                bonus = self.config.user_health.high_balance_bonus
                health_score += bonus
                logger.debug(f"Applied high balance bonus: +{bonus} (balance: {total_balance})")
            
            # Activity factors
            if recent_transactions > 0:
                bonus = self.config.user_health.activity_bonus
                health_score += bonus
                logger.debug(f"Applied activity bonus: +{bonus}")
            if recent_transactions > self.config.user_health.high_activity_threshold:
                bonus = self.config.user_health.high_activity_bonus
                health_score += bonus
                logger.debug(f"Applied high activity bonus: +{bonus} (transactions: {recent_transactions})")
            
            # Debt factors
            if debt_ratio > self.config.debt.high_debt_ratio:
                penalty = self.config.debt.high_debt_penalty - 5  # Slightly less penalty for user-level
                health_score -= penalty
                logger.debug(f"Applied high debt ratio penalty: -{penalty}")
            elif debt_ratio > self.config.debt.moderate_debt_ratio:
                penalty = self.config.debt.moderate_debt_penalty
                health_score -= penalty
                logger.debug(f"Applied moderate debt ratio penalty: -{penalty}")
            
            # Investment factors
            if investment_ratio > self.config.investment.good_investment_ratio - 0.1:  # Slightly lower threshold
                bonus = self.config.investment.good_investment_bonus + 5  # Higher bonus for user level
                health_score += bonus
                logger.debug(f"Applied good investment bonus: +{bonus}")
            elif investment_ratio > self.config.investment.min_investment_ratio:
                bonus = self.config.investment.good_investment_bonus
                health_score += bonus
                logger.debug(f"Applied basic investment bonus: +{bonus}")
            
            # Net worth factors
            if net_worth < 0:
                penalty = self.config.user_health.negative_net_worth_penalty
                health_score -= penalty
                logger.debug(f"Applied negative net worth penalty: -{penalty}")
            elif net_worth > self.config.user_health.excellent_net_worth_threshold / 100:  # Convert cents to dollars
                bonus = self.config.user_health.excellent_net_worth_bonus
                health_score += bonus
                logger.debug(f"Applied excellent net worth bonus: +{bonus} (net worth: {net_worth})")
            
            grade = self._calculate_health_grade(health_score)
            final_score = max(self.config.scoring.min_score, min(self.config.scoring.max_score, health_score))
            
            logger.debug(f"Final user health score: {final_score}, grade: {grade}")
            
            return {
                'overall_score': final_score,
                'grade': grade,
                'net_worth': net_worth,
                'total_liquid': total_liquid,
                'total_debt': total_debt,
                'total_investment': total_investment,
                'debt_ratio': debt_ratio,
                'investment_ratio': investment_ratio,
                'account_count': account_count,
                'recent_activity': recent_transactions,
                'recommendations': self._generate_health_recommendations(
                    final_score, debt_ratio, investment_ratio, net_worth, total_liquid
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate user financial health: {e}")
            return {
                'overall_score': 0,
                'grade': 'F',
                'error': str(e),
                'recommendations': ['Error calculating financial health - please try again']
            }
    
    def _calculate_health_grade(self, score: int) -> str:
        """Convert numerical score to letter grade"""
        if score >= self.config.scoring.grade_a_threshold:
            return 'A'
        elif score >= self.config.scoring.grade_b_threshold:
            return 'B'
        elif score >= self.config.scoring.grade_c_threshold:
            return 'C'
        elif score >= self.config.scoring.grade_d_threshold:
            return 'D'
        else:
            return 'F'
    
    def _generate_health_recommendations(
        self, 
        score: int, 
        debt_ratio: float, 
        investment_ratio: float, 
        net_worth: float, 
        total_liquid: float
    ) -> List[str]:
        """Generate personalized recommendations based on financial health metrics"""
        recommendations = []
        
        # Debt recommendations
        if debt_ratio > self.config.debt.high_debt_ratio:
            recommendations.append("🚨 High debt ratio detected - prioritize paying down high-interest debt")
        elif debt_ratio > self.config.debt.moderate_debt_ratio:
            recommendations.append("⚠️ Monitor debt levels - consider debt consolidation if rates are high")
        
        # Investment recommendations
        if investment_ratio < self.config.investment.min_investment_ratio and total_liquid > self.config.recommendations.investment_starter_liquid / 100:
            recommendations.append("📈 Consider starting to invest for long-term growth")
        elif investment_ratio < self.config.investment.good_investment_ratio and total_liquid > self.config.recommendations.investment_increase_liquid / 100:
            recommendations.append("💰 Increase investment allocation for better long-term returns")
        
        # Emergency fund recommendations
        if total_liquid < self.config.recommendations.emergency_fund_minimum / 100:
            recommendations.append("🚨 Build an emergency fund - aim for $1,000 as a first goal")
        elif total_liquid < self.config.recommendations.emergency_fund_good / 100:
            recommendations.append("💪 Continue building emergency fund - aim for 3-6 months of expenses")
        
        # Net worth recommendations
        if net_worth < 0:
            recommendations.append("🎯 Focus on debt reduction to improve net worth")
        elif net_worth > 0 and investment_ratio < 0.15:
            recommendations.append("🌱 Good foundation! Consider increasing investments for growth")
        
        # Score-based recommendations
        if score < self.config.recommendations.advisor_score_threshold:
            recommendations.append("📋 Consider meeting with a financial advisor for personalized guidance")
        elif score >= self.config.recommendations.excellent_score_threshold:
            recommendations.append("🎉 Great financial health! Keep up the good work")
        
        # Default recommendation if none apply
        if not recommendations:
            recommendations.append("📊 Continue monitoring your financial health regularly")
        
        return recommendations
    
    def calculate_account_health(
        self, 
        account: Account, 
        reconciliation: Dict[str, Any]
    ) -> AccountHealthData:
        """Calculate comprehensive account health including connection and reconciliation status"""
        
        # Calculate connection health
        connection_health = self._calculate_connection_health(account)
        
        # Calculate overall health score
        health_score = self._calculate_account_health_score(reconciliation, connection_health.health_status)
        
        # Generate recommendations
        recommendations = self._generate_account_health_recommendations(
            reconciliation, connection_health.health_status, account
        )
        
        # Build reconciliation health data
        reconciliation_health = ReconciliationHealth(
            is_reconciled=reconciliation['is_reconciled'],
            discrepancy=reconciliation['discrepancy'],
            last_reconciliation=reconciliation['reconciliation_date'],
            transaction_count=reconciliation['transaction_count']
        )
        
        # Build account health data
        health_data = AccountHealthData(
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            is_active=account.is_active,
            current_balance=account.balance_cents / 100,
            currency=account.currency,
            reconciliation=reconciliation_health,
            connection=connection_health,
            health_score=health_score,
            recommendations=recommendations
        )
        
        logger.debug(f"Calculated account health for {account.id}: score={health_score}, status={connection_health.health_status}")
        return health_data
    
    def _calculate_connection_health(self, account: Account) -> ConnectionHealth:
        """Calculate connection health status for an account"""
        connection_health = "not_connected"
        last_sync = None
        sync_frequency = None
        
        if account.plaid_access_token:
            metadata = account.account_metadata or {}
            last_sync = metadata.get('last_sync')
            
            if last_sync:
                try:
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
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid sync date format for account {account.id}: {last_sync}, error: {e}")
                    connection_health = "failed"
        
        return ConnectionHealth(
            health_status=connection_health,
            is_plaid_connected=bool(account.plaid_access_token),
            last_sync=last_sync,
            sync_frequency=sync_frequency
        )
    
    def _calculate_account_health_score(self, reconciliation: Dict[str, Any], connection_health: str) -> int:
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
    
    def _generate_account_health_recommendations(
        self,
        reconciliation: Dict[str, Any], 
        connection_health: str, 
        account: Account
    ) -> List[str]:
        """Generate health improvement recommendations for an account"""
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


# Create singleton instance - will be initialized with config when settings are loaded
financial_health_service = None

def get_financial_health_service(config: Optional[FinancialHealthConfig] = None) -> FinancialHealthService:
    """Get or create the financial health service instance"""
    global financial_health_service
    if financial_health_service is None or config is not None:
        financial_health_service = FinancialHealthService(config)
    return financial_health_service