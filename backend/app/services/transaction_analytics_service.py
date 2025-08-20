"""
Transaction Analytics Service
Handles analytics, summaries, and trend calculations for transactions
Extracted from TransactionService for better separation of concerns
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID

from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class TransactionAnalyticsService:
    """Service for transaction analytics and reporting"""
    
    @staticmethod
    def get_dashboard_analytics(
        db: Session, 
        user_id: UUID, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard analytics for a user"""
        
        # If no date range provided, use current month
        if not start_date:
            now = datetime.now()
            start_date = datetime(now.year, now.month, 1)
        if not end_date:
            end_date = datetime.now()

        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )

        # Get all transactions in the period
        transactions = query.all()

        # Calculate totals (convert from cents to dollars)
        total_income = sum(t.amount_cents for t in transactions if t.amount_cents > 0) / 100.0
        total_expenses = sum(abs(t.amount_cents) for t in transactions if t.amount_cents < 0) / 100.0
        net_amount = total_income - total_expenses

        # Get category breakdown
        category_stats = {}
        for transaction in transactions:
            # Try to get category name if there's a relationship
            category_name = "Uncategorized"  # Default name
            if hasattr(transaction, 'category') and transaction.category:
                category_name = transaction.category.name
            elif transaction.category_id:
                category_name = f"Category {transaction.category_id}"
            
            if category_name not in category_stats:
                category_stats[category_name] = {
                    "total_amount": 0,
                    "transaction_count": 0,
                    "category_name": category_name
                }
            category_stats[category_name]["total_amount"] += abs(transaction.amount_cents / 100.0)
            category_stats[category_name]["transaction_count"] += 1

        # Convert to list and calculate percentages
        category_breakdown = []
        total_for_percentage = total_expenses if total_expenses > 0 else 1  # Avoid division by zero
        
        for category, stats in category_stats.items():
            percentage = (stats["total_amount"] / total_for_percentage) * 100
            category_breakdown.append({
                "category_name": category,
                "total_amount": stats["total_amount"],
                "transaction_count": stats["transaction_count"],
                "percentage": round(percentage, 2)
            })

        # Sort by total amount descending
        category_breakdown.sort(key=lambda x: x["total_amount"], reverse=True)

        # Get recent transactions (last 10)
        recent_transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.transaction_date.desc()).limit(10).all()

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_amount": net_amount,
                "transaction_count": len(transactions)
            },
            "category_breakdown": category_breakdown,
            "recent_transactions": [
                {
                    "id": t.id,
                    "amount": t.amount_cents / 100.0,
                    "category": t.category.name if hasattr(t, 'category') and t.category else "Uncategorized",
                    "description": t.description,
                    "transaction_date": t.transaction_date.isoformat(),
                    "transaction_type": "income" if t.amount_cents > 0 else "expense"
                } for t in recent_transactions
            ]
        }

    @staticmethod
    def get_transaction_summary(
        db: Session, 
        user_id: UUID, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None, 
        category_id: Optional[UUID] = None, 
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transaction summary statistics matching the frontend TransactionSummary interface"""
        
        # Build base query
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        # Apply filters
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if category_id:
            if category_id == '__uncategorized__':
                query = query.filter(Transaction.category_id.is_(None))
            else:
                query = query.filter(Transaction.category_id == category_id)
        if search_query:
            search = f"%{search_query}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search),
                    Transaction.merchant.ilike(search)
                )
            )
        
        # Get all matching transactions
        transactions = query.all()
        
        # Calculate summary statistics
        total_income = sum(t.amount_cents for t in transactions if t.amount_cents > 0) / 100.0
        total_expenses = sum(abs(t.amount_cents) for t in transactions if t.amount_cents < 0) / 100.0
        net_amount = total_income - total_expenses
        transaction_count = len(transactions)
        
        # Calculate category breakdown
        category_stats = {}
        total_for_percentage = total_expenses if total_expenses > 0 else 1
        
        for transaction in transactions:
            # Get category info (assuming there's a relationship)
            category_id_str = str(transaction.category_id) if transaction.category_id else "uncategorized"
            category_name = "Uncategorized"  # Default name
            
            # Try to get category name if there's a relationship
            if hasattr(transaction, 'category') and transaction.category:
                category_name = transaction.category.name
            
            if category_id_str not in category_stats:
                category_stats[category_id_str] = {
                    "categoryId": category_id_str,
                    "categoryName": category_name,
                    "totalAmount": 0.0,
                    "transactionCount": 0
                }
            
            category_stats[category_id_str]["totalAmount"] += abs(transaction.amount_cents) / 100.0
            category_stats[category_id_str]["transactionCount"] += 1
        
        # Convert to list and add percentages
        category_breakdown = []
        for category_id_str, stats in category_stats.items():
            percentage = (stats["totalAmount"] / total_for_percentage) * 100 if total_for_percentage > 0 else 0
            category_breakdown.append({
                "categoryId": stats["categoryId"],
                "categoryName": stats["categoryName"], 
                "totalAmount": stats["totalAmount"],
                "transactionCount": stats["transactionCount"],
                "percentage": round(percentage, 2)
            })
        
        # Sort by total amount descending
        category_breakdown.sort(key=lambda x: x["totalAmount"], reverse=True)
        
        # Calculate additional statistics  
        income_count = sum(1 for t in transactions if t.amount_cents > 0)
        expense_count = sum(1 for t in transactions if t.amount_cents < 0)
        average_transaction = (total_income + total_expenses) / transaction_count if transaction_count > 0 else 0
        
        return {
            # Main stats for compatibility
            "totalIncome": total_income,
            "totalExpenses": total_expenses, 
            "netAmount": net_amount,
            "transactionCount": transaction_count,
            "categoryBreakdown": category_breakdown,
            
            # Additional stats to match frontend TransactionStats interface
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_amount": net_amount,
            "total_count": transaction_count,
            "transaction_count": transaction_count,
            "average_transaction": average_transaction,
            "transaction_count_by_type": {
                "income": income_count,
                "expense": expense_count
            }
        }

    @staticmethod
    def get_spending_trends(db: Session, user_id: UUID, period: str = "monthly") -> List[Dict[str, Any]]:
        """Get spending trends over time"""
        
        # Calculate date range based on period
        now = datetime.now()
        if period == "weekly":
            start_date = now - timedelta(weeks=12)  # Last 12 weeks
        else:  # monthly
            start_date = now - timedelta(days=365)  # Last 12 months

        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date
        )

        transactions = query.all()

        # Group by time period
        trends = {}
        for transaction in transactions:
            if period == "weekly":
                # Get week number and year
                year = transaction.transaction_date.year
                week = transaction.transaction_date.isocalendar()[1]
                key = f"{year}-W{week:02d}"
                display_date = transaction.transaction_date.strftime("%Y-W%U")
            else:  # monthly
                key = transaction.transaction_date.strftime("%Y-%m")
                display_date = transaction.transaction_date.strftime("%Y-%m")

            if key not in trends:
                trends[key] = {
                    "period": display_date,
                    "income": 0,
                    "expenses": 0,
                    "net": 0
                }

            if transaction.amount_cents > 0:
                trends[key]["income"] += transaction.amount_cents / 100.0
            else:
                trends[key]["expenses"] += abs(transaction.amount_cents / 100.0)
            trends[key]["net"] = trends[key]["income"] - trends[key]["expenses"]

        # Convert to sorted list
        trend_list = list(trends.values())
        trend_list.sort(key=lambda x: x["period"])

        return trend_list
    
    @staticmethod
    def get_category_spending_analysis(
        db: Session, 
        user_id: UUID, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get detailed category spending analysis"""
        
        # Build query with date filtering
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        
        transactions = query.all()
        
        # Group by category
        category_analysis = {}
        total_expenses = 0
        
        for transaction in transactions:
            if transaction.amount_cents >= 0:  # Skip income
                continue
                
            category_name = "Uncategorized"
            category_id = "uncategorized"
            
            if hasattr(transaction, 'category') and transaction.category:
                category_name = transaction.category.name
                category_id = str(transaction.category_id)
            
            if category_id not in category_analysis:
                category_analysis[category_id] = {
                    "category_id": category_id,
                    "category_name": category_name,
                    "total_amount": 0,
                    "transaction_count": 0,
                    "average_amount": 0,
                    "transactions": []
                }
            
            amount = abs(transaction.amount_cents) / 100.0
            category_analysis[category_id]["total_amount"] += amount
            category_analysis[category_id]["transaction_count"] += 1
            category_analysis[category_id]["transactions"].append({
                "id": str(transaction.id),
                "amount": amount,
                "description": transaction.description,
                "date": transaction.transaction_date.isoformat(),
                "merchant": transaction.merchant
            })
            
            total_expenses += amount
        
        # Calculate averages and percentages
        for category_data in category_analysis.values():
            category_data["average_amount"] = (
                category_data["total_amount"] / category_data["transaction_count"]
                if category_data["transaction_count"] > 0 else 0
            )
            category_data["percentage"] = (
                (category_data["total_amount"] / total_expenses) * 100
                if total_expenses > 0 else 0
            )
        
        # Sort by total amount and limit results
        sorted_categories = sorted(
            category_analysis.values(), 
            key=lambda x: x["total_amount"], 
            reverse=True
        )[:limit]
        
        return {
            "total_expenses": total_expenses,
            "categories": sorted_categories,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }


# Create singleton instance
transaction_analytics_service = TransactionAnalyticsService()