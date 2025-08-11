import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from uuid import UUID

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category

logger = logging.getLogger(__name__)

class AnalyticsService:
    async def get_dashboard_summary(self, db: Session, user_id: UUID) -> dict:
        """
        Generates a summary of dashboard analytics for a user.
        """
        try:
            # Calculate total balance from all accounts
            total_balance_cents = db.query(func.sum(Account.balance_cents)).filter(
                Account.user_id == user_id
            ).scalar() or 0

            # Get total number of transactions
            total_transactions = db.query(func.count(Transaction.id)).filter(
                Transaction.user_id == user_id
            ).scalar() or 0

            # Get 5 most recent transactions
            recent_transactions_query = db.query(Transaction).filter(
                Transaction.user_id == user_id
            ).order_by(desc(Transaction.transaction_date)).limit(5).all()
            
            recent_transactions = [
                {
                    "id": str(t.id),
                    "description": t.description,
                    "amountCents": t.amount_cents,
                    "date": t.transaction_date.isoformat()
                } for t in recent_transactions_query
            ]

            # Get spending by category
            spending_by_category_query = db.query(
                Category.name,
                func.sum(Transaction.amount_cents).label('total_spent')
            ).join(Category, Transaction.category_id == Category.id).filter(
                Transaction.user_id == user_id,
                Transaction.amount_cents < 0  # Only expenses
            ).group_by(Category.name).order_by(desc('total_spent')).limit(5).all()
            
            spending_by_category = {name: abs(total) for name, total in spending_by_category_query}

            return {
                "totalBalance": total_balance_cents / 100,
                "totalTransactions": total_transactions,
                "recentTransactions": recent_transactions,
                "spendingByCategory": spending_by_category,
            }
        except Exception as e:
            logger.error(f"Error generating dashboard summary for user {user_id}: {e}", exc_info=True)
            # Return a default structure on error
            return {"totalBalance": 0, "totalTransactions": 0, "recentTransactions": [], "spendingByCategory": {}}

analytics_service = AnalyticsService()