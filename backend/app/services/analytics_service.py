import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from uuid import UUID
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.goal import Goal

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

            # Get 10 most recent transactions (displayed in scrollable container)
            recent_transactions_query = db.query(Transaction).filter(
                Transaction.user_id == user_id
            ).order_by(desc(Transaction.transaction_date)).limit(10).all()
            
            recent_transactions = [
                {
                    "id": str(t.id),
                    "description": t.description,
                    "amountCents": t.amount_cents,  # Keep raw values - negative for expenses, positive for income
                    "amount": t.amount_cents / 100.0,  # Keep raw dollar amount for proper sign display
                    "type": "income" if t.amount_cents > 0 else "expense",  # Add transaction type
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

            # Calculate financial summary using same logic as transaction service
            # Get all transactions for this user to calculate income/expense breakdown
            all_transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
            
            # Calculate totals (convert from cents to dollars)
            total_income = sum(t.amount_cents for t in all_transactions if t.amount_cents > 0) / 100.0
            total_expenses = sum(abs(t.amount_cents) for t in all_transactions if t.amount_cents < 0) / 100.0
            net_amount = total_income - total_expenses
            transaction_count = len(all_transactions)
            
            # Count income vs expense transactions
            income_count = sum(1 for t in all_transactions if t.amount_cents > 0)
            expense_count = sum(1 for t in all_transactions if t.amount_cents < 0)
            average_transaction = (total_income + total_expenses) / transaction_count if transaction_count > 0 else 0

            return {
                # Original format for backward compatibility
                "totalBalance": total_balance_cents / 100,
                "totalTransactions": total_transactions,
                "recentTransactions": recent_transactions,
                "spendingByCategory": spending_by_category,
                
                # New summary format expected by frontend dashboard
                "summary": {
                    "total_income": total_income,
                    "total_expenses": total_expenses,
                    "net_amount": net_amount,
                    "transaction_count": transaction_count,
                    "average_transaction": average_transaction,
                    "transaction_count_by_type": {
                        "income": income_count,
                        "expense": expense_count
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error generating dashboard summary for user {user_id}: {e}", exc_info=True)
            # Return a default structure on error
            return {
                "totalBalance": 0, 
                "totalTransactions": 0, 
                "recentTransactions": [], 
                "spendingByCategory": {},
                "summary": {
                    "total_income": 0,
                    "total_expenses": 0,
                    "net_amount": 0,
                    "transaction_count": 0,
                    "average_transaction": 0,
                    "transaction_count_by_type": {
                        "income": 0,
                        "expense": 0
                    }
                }
            }

    async def get_spending_heatmap_data(self, db: Session, user_id: UUID, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Aggregates total daily expenses for a calendar heatmap visualization.
        Returns data in format expected by Nivo Calendar component.
        """
        try:
            daily_expenses = db.query(
                func.date(Transaction.transaction_date).label('day'),
                func.sum(func.abs(Transaction.amount_cents)).label('value')
            ).filter(
                Transaction.user_id == user_id,
                Transaction.amount_cents < 0,  # Only expenses
                Transaction.transaction_date.between(start_date, end_date)
            ).group_by(func.date(Transaction.transaction_date)).all()

            # Format the data for the Nivo chart - convert to list of dicts
            heatmap_data = [
                {"day": result.day.isoformat(), "value": int(result.value)}
                for result in daily_expenses
            ]
            
            return heatmap_data
        except Exception as e:
            logger.error(f"Error generating spending heatmap data for user {user_id}: {e}", exc_info=True)
            return []

    async def get_money_flow_data(self, db: Session, user_id: UUID, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Generates money flow data for Sankey diagram visualization.
        Returns nodes and links structure suitable for Sankey charts.
        """
        try:
            # Get all income transactions, grouped by category
            income_query = db.query(
                Category.name,
                func.sum(Transaction.amount_cents).label('total_amount')
            ).join(
                Transaction, Transaction.category_id == Category.id
            ).filter(
                Transaction.user_id == user_id,
                Transaction.amount_cents > 0,  # Only income
                Transaction.transaction_date.between(start_date, end_date)
            ).group_by(Category.name).all()

            # Get all expense transactions, grouped by category, limited to top 10
            expense_query = db.query(
                Category.name,
                func.sum(func.abs(Transaction.amount_cents)).label('total_amount')
            ).join(
                Transaction, Transaction.category_id == Category.id
            ).filter(
                Transaction.user_id == user_id,
                Transaction.amount_cents < 0,  # Only expenses
                Transaction.transaction_date.between(start_date, end_date)
            ).group_by(Category.name).order_by(
                func.sum(func.abs(Transaction.amount_cents)).desc()
            ).limit(10).all()

            # Structure data for Sankey diagram
            nodes: List[Dict[str, str]] = [{"id": "Total Income"}]
            links: List[Dict[str, Any]] = []
            
            total_income_cents = 0
            
            # From Income Sources to "Total Income" node
            for category_name, amount_cents in income_query:
                if amount_cents and amount_cents > 0:
                    node_name = f"Income: {category_name}"
                    nodes.append({"id": node_name})
                    # Convert cents to dollars for display
                    amount_dollars = amount_cents / 100
                    links.append({
                        "source": node_name, 
                        "target": "Total Income", 
                        "value": amount_dollars
                    })
                    total_income_cents += amount_cents

            # From "Total Income" node to Expense Categories
            total_expenses_cents = 0
            for category_name, amount_cents in expense_query:
                if amount_cents and amount_cents > 0:
                    node_name = f"Expense: {category_name}"
                    nodes.append({"id": node_name})
                    # Convert cents to dollars for display
                    amount_dollars = amount_cents / 100
                    links.append({
                        "source": "Total Income", 
                        "target": node_name, 
                        "value": amount_dollars
                    })
                    total_expenses_cents += amount_cents

            # Add a node for savings/unaccounted money if there's a positive balance
            net_savings_cents = total_income_cents - total_expenses_cents
            if net_savings_cents > 0:
                nodes.append({"id": "Savings/Unaccounted"})
                savings_dollars = net_savings_cents / 100
                links.append({
                    "source": "Total Income", 
                    "target": "Savings/Unaccounted", 
                    "value": savings_dollars
                })

            # Calculate totals for metadata
            total_income_dollars = total_income_cents / 100
            total_expenses_dollars = total_expenses_cents / 100
            net_savings_dollars = net_savings_cents / 100

            return {
                "nodes": nodes,
                "links": links,
                "metadata": {
                    "total_income": total_income_dollars,
                    "total_expenses": total_expenses_dollars,
                    "net_savings": net_savings_dollars,
                    "date_range": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "income_sources_count": len(income_query),
                    "expense_categories_count": len(expense_query)
                }
            }
        except Exception as e:
            logger.error(f"Error generating money flow data for user {user_id}: {e}", exc_info=True)
            # Return empty structure on error
            return {
                "nodes": [{"id": "Total Income"}],
                "links": [],
                "metadata": {
                    "total_income": 0,
                    "total_expenses": 0,
                    "net_savings": 0,
                    "date_range": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "income_sources_count": 0,
                    "expense_categories_count": 0
                }
            }

    async def get_financial_timeline(
        self, 
        db: Session, 
        user_id: UUID, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """
        Aggregates financial timeline events from multiple sources.
        
        Combines goal milestones and significant transactions
        into a unified timeline of financial events.
        """
        try:
            timeline_events = []
            
            # 1. Get goal-related events (created OR completed in date range)
            goals_query = db.query(Goal).filter(
                Goal.user_id == user_id,
                or_(
                    Goal.created_at.between(start_date, end_date),
                    Goal.completed_date.between(start_date, end_date)
                )
            ).all()
            
            for goal in goals_query:
                # Goal creation event (if created in date range)
                if (goal.created_at and start_date <= goal.created_at.date() <= end_date):
                    timeline_events.append({
                        "id": f"goal_created_{goal.id}",
                        "date": goal.created_at.date().isoformat(),
                        "type": "goal_created",
                        "title": f"Started Goal: {goal.name}",
                        "description": f"Set target of ${goal.target_amount_cents / 100:.2f}",
                        "icon": "🎯",
                        "color": "#10b981",
                        "source": "goal_system",
                        "extra_data": {
                            "goal_id": str(goal.id),
                            "target_amount": goal.target_amount_cents,
                            "goal_type": goal.goal_type.value
                        },
                        "created_at": goal.created_at.isoformat() if goal.created_at else None
                    })
                
                # Goal completion event (if completed in date range)
                if (goal.is_achieved and goal.completed_date and 
                    start_date <= goal.completed_date <= end_date):
                    timeline_events.append({
                        "id": f"goal_completed_{goal.id}",
                        "date": goal.completed_date.isoformat(),
                        "type": "goal_completed",
                        "title": f"Achieved Goal: {goal.name}",
                        "description": f"Reached target of ${goal.target_amount_cents / 100:.2f}",
                        "icon": "🏆",
                        "color": "#f59e0b",
                        "source": "goal_system",
                        "extra_data": {
                            "goal_id": str(goal.id),
                            "target_amount": goal.target_amount_cents,
                            "actual_amount": goal.current_amount_cents,
                            "goal_type": goal.goal_type.value
                        },
                        "created_at": goal.completed_date.isoformat() if goal.completed_date else None
                    })
            
            # 3. Get significant transactions (threshold: $500)
            significant_threshold = 50000  # $500 in cents
            
            significant_transactions_query = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date.between(start_date, end_date),
                func.abs(Transaction.amount_cents) >= significant_threshold
            ).order_by(desc(Transaction.amount_cents)).limit(20).all()  # Limit to top 20
            
            for transaction in significant_transactions_query:
                # Determine event type and styling based on transaction amount
                is_income = transaction.amount_cents > 0
                amount_dollars = abs(transaction.amount_cents) / 100
                
                timeline_events.append({
                    "id": f"transaction_{transaction.id}",
                    "date": transaction.transaction_date.isoformat(),
                    "type": "significant_transaction",
                    "title": f"{'Large Income' if is_income else 'Large Expense'}: ${amount_dollars:.2f}",
                    "description": transaction.description or "No description",
                    "icon": "💰" if is_income else "💸",
                    "color": "#10b981" if is_income else "#ef4444",
                    "source": "transaction_system",
                    "extra_data": {
                        "transaction_id": str(transaction.id),
                        "amount_cents": transaction.amount_cents,
                        "category_id": str(transaction.category_id) if transaction.category_id else None,
                        "account_id": str(transaction.account_id) if transaction.account_id else None
                    },
                    "created_at": transaction.created_at.isoformat() if transaction.created_at else None
                })
            
            # 4. Sort all events by date (most recent first)
            timeline_events.sort(key=lambda x: x["date"], reverse=True)
            
            return {
                "events": timeline_events,
                "total_count": len(timeline_events),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "metadata": {
                    "annotations_count": len(annotations_query),
                    "goals_count": len(goals_query),
                    "significant_transactions_count": len(significant_transactions_query),
                    "significant_threshold_dollars": significant_threshold / 100
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating financial timeline for user {user_id}: {e}", exc_info=True)
            return {
                "events": [],
                "total_count": 0,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "metadata": {
                    "annotations_count": 0,
                    "goals_count": 0,
                    "significant_transactions_count": 0,
                    "significant_threshold_dollars": significant_threshold / 100
                }
            }

    async def get_net_worth_trend(self, db: Session, user_id: UUID, period: str = '90d') -> List[Dict[str, Any]]:
        """
        Calculate net worth trend over time by aggregating account balances at different points.
        Since we don't store historical balance data, we calculate it based on transactions.
        
        Args:
            period: Time period for the trend ('90d', '1y', 'all')
        """
        try:
            # Determine date range based on period
            end_date = datetime.utcnow().date()
            if period == '90d':
                start_date = end_date - timedelta(days=90)
                interval_days = 7  # Weekly data points
            elif period == '1y':
                start_date = end_date - timedelta(days=365)
                interval_days = 30  # Monthly data points
            else:  # 'all'
                # Get the earliest transaction date
                earliest_tx = db.query(func.min(Transaction.transaction_date)).filter(
                    Transaction.user_id == user_id
                ).scalar()
                start_date = earliest_tx if earliest_tx else end_date - timedelta(days=90)
                total_days = (end_date - start_date).days
                interval_days = max(7, total_days // 20)  # Aim for ~20 data points
            
            # Get current account balances
            current_accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).all()
            
            if not current_accounts:
                return []
            
            current_net_worth = sum(account.balance_cents for account in current_accounts)
            
            # Generate data points by going backwards in time
            data_points = []
            current_date = end_date
            
            while current_date >= start_date:
                # Calculate net worth at this date by subtracting future transactions from current balance
                future_transactions = db.query(func.sum(Transaction.amount_cents)).filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date > current_date
                ).scalar() or 0
                
                # Net worth at this date = current balance - future transactions
                net_worth_at_date = current_net_worth - future_transactions
                
                data_points.append({
                    "date": current_date.isoformat(),
                    "net_worth_cents": int(net_worth_at_date),
                    "net_worth": net_worth_at_date / 100
                })
                
                current_date -= timedelta(days=interval_days)
            
            # Sort chronologically (oldest first)
            data_points.reverse()
            
            return data_points
            
        except Exception as e:
            logger.error(f"Error generating net worth trend for user {user_id}: {e}", exc_info=True)
            return []

    async def get_cash_flow_waterfall(self, db: Session, user_id: UUID, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Generate cash flow waterfall data showing how balance changes from start to end.
        Shows: Starting Balance → Income → Expenses → Ending Balance
        """
        try:
            # Get current account balances
            current_accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).all()
            
            if not current_accounts:
                return {
                    "start_balance_cents": 0,
                    "total_income_cents": 0,
                    "total_expenses_cents": 0,
                    "end_balance_cents": 0,
                    "start_balance": 0,
                    "total_income": 0,
                    "total_expenses": 0,
                    "end_balance": 0
                }
            
            current_balance_cents = sum(account.balance_cents for account in current_accounts)
            
            # Get transactions in the period
            period_transactions = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date.between(start_date, end_date)
            ).all()
            
            # Calculate totals
            total_income_cents = sum(tx.amount_cents for tx in period_transactions if tx.amount_cents > 0)
            total_expenses_cents = sum(abs(tx.amount_cents) for tx in period_transactions if tx.amount_cents < 0)
            
            # Calculate starting balance (current balance minus period net change)
            period_net_change = total_income_cents - total_expenses_cents
            start_balance_cents = current_balance_cents - period_net_change
            
            return {
                "start_balance_cents": int(start_balance_cents),
                "total_income_cents": int(total_income_cents),
                "total_expenses_cents": int(total_expenses_cents),
                "end_balance_cents": int(current_balance_cents),
                "start_balance": start_balance_cents / 100,
                "total_income": total_income_cents / 100,
                "total_expenses": total_expenses_cents / 100,
                "end_balance": current_balance_cents / 100
            }
            
        except Exception as e:
            logger.error(f"Error generating cash flow waterfall for user {user_id}: {e}", exc_info=True)
            return {
                "start_balance_cents": 0,
                "total_income_cents": 0,
                "total_expenses_cents": 0,
                "end_balance_cents": 0,
                "start_balance": 0,
                "total_income": 0,
                "total_expenses": 0,
                "end_balance": 0
            }

analytics_service = AnalyticsService()