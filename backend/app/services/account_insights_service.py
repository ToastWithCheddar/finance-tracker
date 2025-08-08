"""
Account categorization and insights service
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget

logger = logging.getLogger(__name__)

class AccountInsightsService:
    """Service for account categorization and intelligent insights"""
    
    def __init__(self):
        pass
    
    def categorize_accounts(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Categorize user accounts with intelligent insights"""
        try:
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).all()
            
            categorization = {
                'user_id': user_id,
                'total_accounts': len(accounts),
                'categories': {
                    'spending': [],  # Checking accounts with high activity
                    'saving': [],   # Savings accounts and low-activity accounts
                    'credit': [],   # Credit cards and lines of credit
                    'investment': [], # Investment and retirement accounts
                    'other': []     # Uncategorized accounts
                },
                'insights': [],
                'recommendations': [],
                'financial_health': {}
            }
            
            # Categorize each account
            for account in accounts:
                account_info = self._analyze_account(db, account)
                category = self._determine_account_category(account, account_info)
                
                categorization['categories'][category].append({
                    'account_id': str(account.id),
                    'name': account.name,
                    'type': account.account_type,
                    'balance': account.balance_cents / 100,
                    'currency': account.currency,
                    'category': category,
                    'insights': account_info['insights'],
                    'activity_level': account_info['activity_level'],
                    'health_score': account_info['health_score']
                })
            
            # Generate overall insights
            categorization['insights'] = self._generate_portfolio_insights(db, user_id, categorization)
            categorization['recommendations'] = self._generate_recommendations(categorization)
            categorization['financial_health'] = self._calculate_financial_health(categorization)
            
            return categorization
            
        except Exception as e:
            logger.error(f"Failed to categorize accounts for user {user_id}: {e}")
            raise
    
    def _analyze_account(self, db: Session, account: Account) -> Dict[str, Any]:
        """Analyze individual account patterns and health"""
        try:
            # Get transaction history for the last 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            transactions = db.query(Transaction).filter(
                Transaction.account_id == account.id,
                Transaction.created_at >= cutoff_date,
                Transaction.status == 'posted'
            ).all()
            
            if not transactions:
                return {
                    'activity_level': 'inactive',
                    'insights': ['No recent transaction activity'],
                    'health_score': 50,
                    'transaction_count': 0,
                    'average_transaction': 0,
                    'spending_pattern': 'unknown'
                }
            
            # Calculate metrics
            total_transactions = len(transactions)
            total_amount = sum(abs(tx.amount_cents) for tx in transactions)
            average_transaction = total_amount / total_transactions if total_transactions > 0 else 0
            
            # Separate income and expenses
            income_transactions = [tx for tx in transactions if tx.amount_cents > 0]
            expense_transactions = [tx for tx in transactions if tx.amount_cents < 0]
            
            total_income = sum(tx.amount_cents for tx in income_transactions)
            total_expenses = sum(abs(tx.amount_cents) for tx in expense_transactions)
            
            # Determine activity level
            daily_avg_transactions = total_transactions / 90
            if daily_avg_transactions > 2:
                activity_level = 'high'
            elif daily_avg_transactions > 0.5:
                activity_level = 'medium'
            elif daily_avg_transactions > 0.1:
                activity_level = 'low'
            else:
                activity_level = 'inactive'
            
            # Generate insights
            insights = []
            
            if activity_level == 'high':
                insights.append(f"Very active account with {total_transactions} transactions in 90 days")
            elif activity_level == 'medium':
                insights.append(f"Moderately active with {total_transactions} transactions")
            elif activity_level == 'low':
                insights.append(f"Low activity account with {total_transactions} transactions")
            
            if average_transaction > 100000:  # $1000+
                insights.append("High-value transactions - likely primary account")
            elif average_transaction < 2000:  # $20
                insights.append("Small transactions - possibly petty cash or savings")
            
            # Balance trend analysis
            if len(transactions) > 10:
                recent_balance_change = account.balance_cents - (total_income - total_expenses)
                if recent_balance_change > 10000:  # $100+
                    insights.append("Balance increasing - good savings pattern")
                elif recent_balance_change < -10000:  # -$100+
                    insights.append("Balance decreasing - monitor spending")
            
            # Health score calculation
            health_score = self._calculate_account_health_score(
                account, total_transactions, activity_level, total_income, total_expenses
            )
            
            return {
                'activity_level': activity_level,
                'insights': insights,
                'health_score': health_score,
                'transaction_count': total_transactions,
                'average_transaction': average_transaction / 100,
                'total_income': total_income / 100,
                'total_expenses': total_expenses / 100,
                'spending_pattern': self._determine_spending_pattern(expense_transactions)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze account {account.id}: {e}")
            return {
                'activity_level': 'unknown',
                'insights': ['Analysis failed'],
                'health_score': 0,
                'transaction_count': 0,
                'average_transaction': 0,
                'spending_pattern': 'unknown'
            }
    
    def _determine_account_category(self, account: Account, analysis: Dict[str, Any]) -> str:
        """Determine the best category for an account based on type and analysis"""
        
        # Primary categorization by account type
        type_mapping = {
            'checking': 'spending',
            'savings': 'saving',
            'credit_card': 'credit',
            'investment': 'investment',
            'retirement': 'investment',
            'mortgage': 'other',
            'loan': 'other'
        }
        
        base_category = type_mapping.get(account.account_type, 'other')
        
        # Refine based on activity and balance
        activity_level = analysis.get('activity_level', 'unknown')
        balance = account.balance_cents / 100
        
        # Override logic for better categorization
        if base_category == 'spending' and activity_level == 'low' and balance > 1000:
            # Low-activity checking account with high balance might be savings
            return 'saving'
        elif base_category == 'saving' and activity_level == 'high':
            # High-activity savings account might be primary spending
            return 'spending'
        
        return base_category
    
    def _determine_spending_pattern(self, expense_transactions: List[Transaction]) -> str:
        """Analyze spending pattern from expense transactions"""
        if not expense_transactions:
            return 'no_expenses'
        
        # Group transactions by day of week and amount
        daily_amounts = {}
        large_transactions = 0
        
        for tx in expense_transactions:
            day = tx.transaction_date.weekday()
            amount = abs(tx.amount_cents)
            
            if day not in daily_amounts:
                daily_amounts[day] = []
            daily_amounts[day].append(amount)
            
            if amount > 10000:  # $100+
                large_transactions += 1
        
        # Determine pattern
        if large_transactions > len(expense_transactions) * 0.3:
            return 'large_purchases'
        elif len(set(daily_amounts.keys())) <= 2:
            return 'concentrated'  # Spending concentrated on few days
        elif all(len(amounts) > 0 for amounts in daily_amounts.values()):
            return 'distributed'  # Even spending across week
        else:
            return 'irregular'
    
    def _calculate_account_health_score(
        self, 
        account: Account, 
        transaction_count: int, 
        activity_level: str, 
        total_income: int, 
        total_expenses: int
    ) -> int:
        """Calculate health score (0-100) for an account"""
        score = 100
        balance = account.balance_cents
        
        # Balance health (40% weight)
        if balance < 0:  # Negative balance
            score -= 30
        elif balance < 10000:  # Less than $100
            score -= 20
        elif balance > 100000:  # More than $1000 - good
            score += 10
        
        # Activity health (30% weight)
        if activity_level == 'inactive':
            score -= 20
        elif activity_level == 'high':
            score += 10
        
        # Cash flow health (30% weight)
        if total_income > 0 and total_expenses > 0:
            net_flow = total_income - abs(total_expenses)
            if net_flow > 0:
                score += 15  # Positive cash flow
            elif net_flow < -50000:  # Spending much more than earning
                score -= 25
        
        # Connection health bonus
        if account.plaid_access_token:
            metadata = account.account_metadata or {}
            last_sync = metadata.get('last_sync')
            if last_sync:
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', ''))
                hours_since_sync = (datetime.utcnow() - last_sync_dt).total_seconds() / 3600
                if hours_since_sync < 24:
                    score += 5  # Recently synced
        
        return max(0, min(100, score))
    
    def _generate_portfolio_insights(
        self, 
        db: Session, 
        user_id: str, 
        categorization: Dict[str, Any]
    ) -> List[str]:
        """Generate insights about the user's overall account portfolio"""
        insights = []
        
        try:
            categories = categorization['categories']
            
            # Account distribution insights
            spending_accounts = len(categories['spending'])
            saving_accounts = len(categories['saving'])
            credit_accounts = len(categories['credit'])
            
            if spending_accounts == 0:
                insights.append("⚠️ No active spending accounts detected - consider connecting your primary checking account")
            elif spending_accounts > 3:
                insights.append("💡 Multiple spending accounts - consider consolidating for better tracking")
            
            if saving_accounts == 0:
                insights.append("💰 No savings accounts detected - consider setting up automatic savings")
            elif saving_accounts > 1:
                insights.append("📈 Good diversification with multiple savings accounts")
            
            if credit_accounts > 3:
                insights.append("⚠️ Multiple credit accounts - monitor debt levels carefully")
            
            # Balance distribution insights
            total_liquid = sum(
                account['balance'] for account in categories['spending'] + categories['saving']
                if account['balance'] > 0
            )
            
            total_debt = sum(
                abs(account['balance']) for account in categories['credit']
                if account['balance'] < 0
            )
            
            if total_liquid > 0 and total_debt > 0:
                debt_ratio = total_debt / total_liquid
                if debt_ratio > 0.5:
                    insights.append("⚠️ High debt-to-liquid ratio - consider debt reduction strategies")
                elif debt_ratio < 0.2:
                    insights.append("✅ Healthy debt-to-liquid ratio")
            
            # Activity insights
            high_activity_accounts = sum(
                1 for category in categories.values() 
                for account in category 
                if account.get('activity_level') == 'high'
            )
            
            if high_activity_accounts == 0:
                insights.append("📊 Low account activity - ensure transactions are being captured")
            elif high_activity_accounts > 2:
                insights.append("📊 High activity across multiple accounts - good financial engagement")
            
            # Health score insights
            avg_health = sum(
                account.get('health_score', 0) for category in categories.values() 
                for account in category
            ) / max(1, categorization['total_accounts'])
            
            if avg_health > 80:
                insights.append("✅ Excellent overall account health")
            elif avg_health > 60:
                insights.append("👍 Good account health with room for improvement")
            elif avg_health > 40:
                insights.append("⚠️ Average account health - some attention needed")
            else:
                insights.append("🚨 Poor account health - immediate attention required")
            
        except Exception as e:
            logger.error(f"Failed to generate portfolio insights: {e}")
            insights.append("Unable to generate insights at this time")
        
        return insights[:8]  # Limit to top 8 insights
    
    def _generate_recommendations(self, categorization: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on account analysis"""
        recommendations = []
        
        try:
            categories = categorization['categories']
            
            # Account structure recommendations
            if len(categories['spending']) == 0:
                recommendations.append("Connect your primary checking account for transaction tracking")
            
            if len(categories['saving']) == 0:
                recommendations.append("Set up a savings account to build emergency fund")
            
            if len(categories['investment']) == 0:
                recommendations.append("Consider opening investment accounts for long-term growth")
            
            # Balance recommendations
            total_checking = sum(
                account['balance'] for account in categories['spending']
                if account['balance'] > 0
            )
            
            total_savings = sum(
                account['balance'] for account in categories['saving']
                if account['balance'] > 0
            )
            
            if total_checking > total_savings * 3 and total_savings > 0:
                recommendations.append("Consider moving excess checking funds to high-yield savings")
            
            if total_savings < total_checking * 0.2:
                recommendations.append("Build emergency fund - aim for 3-6 months of expenses")
            
            # Activity recommendations
            inactive_accounts = [
                account for category in categories.values() 
                for account in category 
                if account.get('activity_level') == 'inactive' and account['balance'] > 100
            ]
            
            if inactive_accounts:
                recommendations.append(f"Review {len(inactive_accounts)} inactive accounts - consider consolidating")
            
            # Health recommendations
            unhealthy_accounts = [
                account for category in categories.values() 
                for account in category 
                if account.get('health_score', 0) < 50
            ]
            
            if unhealthy_accounts:
                recommendations.append(f"Address health issues in {len(unhealthy_accounts)} accounts")
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate recommendations at this time")
        
        return recommendations[:6]  # Limit to top 6 recommendations
    
    def _calculate_financial_health(self, categorization: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall financial health metrics"""
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
            health_score = 100
            
            if debt_ratio > 0.5:
                health_score -= 30
            elif debt_ratio > 0.3:
                health_score -= 15
            
            if investment_ratio < 0.1 and total_liquid > 1000:
                health_score -= 20
            elif investment_ratio > 0.3:
                health_score += 10
            
            if net_worth < 0:
                health_score -= 25
            elif net_worth > 10000:
                health_score += 15
            
            # Health grade
            if health_score >= 90:
                grade = 'A'
            elif health_score >= 80:
                grade = 'B'
            elif health_score >= 70:
                grade = 'C'
            elif health_score >= 60:
                grade = 'D'
            else:
                grade = 'F'
            
            return {
                'overall_score': max(0, min(100, health_score)),
                'grade': grade,
                'net_worth': net_worth,
                'total_liquid': total_liquid,
                'total_debt': total_debt,
                'total_investment': total_investment,
                'debt_ratio': debt_ratio,
                'investment_ratio': investment_ratio,
                'account_diversity': len([cat for cat in categories.values() if len(cat) > 0])
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate financial health: {e}")
            return {
                'overall_score': 0,
                'grade': 'F',
                'error': str(e)
            }

# Create global service instance
account_insights_service = AccountInsightsService()