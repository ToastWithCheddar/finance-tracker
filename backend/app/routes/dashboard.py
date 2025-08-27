"""
Dashboard API endpoints.
Provides dashboard data including net worth trends and financial insights.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.services.financial_health_service import get_financial_health_service
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_dashboard_data(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    category_id: Optional[str] = Query(None, description="Category filter"),
    account_id: Optional[str] = Query(None, description="Account filter"),
    amount_min: Optional[float] = Query(None, description="Minimum amount filter"),
    amount_max: Optional[float] = Query(None, description="Maximum amount filter"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get filtered dashboard data including summary metrics"""
    try:
        # Parse date filters
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Get financial health service and calculate user financial health
        health_service = get_financial_health_service()
        financial_health = health_service.calculate_user_financial_health(db, current_user.id)
        
        # Build transaction query with filters
        transaction_query = db.query(Transaction).filter(
            Transaction.user_id == current_user.id
        )
        
        if parsed_start_date:
            transaction_query = transaction_query.filter(
                Transaction.transaction_date >= parsed_start_date
            )
        
        if parsed_end_date:
            transaction_query = transaction_query.filter(
                Transaction.transaction_date <= parsed_end_date
            )
        
        if category_id:
            transaction_query = transaction_query.filter(
                Transaction.category_id == category_id
            )
        
        if account_id:
            transaction_query = transaction_query.filter(
                Transaction.account_id == account_id
            )
        
        if amount_min is not None:
            transaction_query = transaction_query.filter(
                Transaction.amount_cents >= int(amount_min * 100)
            )
        
        if amount_max is not None:
            transaction_query = transaction_query.filter(
                Transaction.amount_cents <= int(amount_max * 100)
            )
        
        # Get filtered transactions count
        filtered_transactions = transaction_query.count()
        
        # Get account count (always include all accounts for now)
        account_count = db.query(Account).filter(
            Account.user_id == current_user.id,
            Account.is_active == True
        ).count()
        
        return {
            "net_worth": financial_health.get("net_worth", 0),
            "total_liquid": financial_health.get("total_liquid", 0),
            "total_debt": financial_health.get("total_debt", 0),
            "total_investment": financial_health.get("total_investment", 0),
            "financial_health_score": financial_health.get("overall_score", 0),
            "financial_health_grade": financial_health.get("grade", "N/A"),
            "account_count": account_count,
            "filtered_transactions": filtered_transactions,
            "recommendations": financial_health.get("recommendations", []),
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "category_id": category_id,
                "account_id": account_id,
                "amount_min": amount_min,
                "amount_max": amount_max
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard data for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard data"
        )


@router.get("/category-breakdown")
async def get_category_breakdown(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get category breakdown for transactions in the specified date range"""
    try:
        # Parse date filters
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Build query to get category breakdown
        # Use outer join from transactions to include uncategorized (NULL category_id)
        query = (
            db.query(
                Category.id.label('category_id'),
                func.coalesce(Category.name, 'Uncategorized').label('category_name'),
                func.sum(Transaction.amount_cents).label('total_amount_cents'),
                func.count(Transaction.id).label('transaction_count')
            )
            .select_from(Transaction)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(Transaction.user_id == current_user.id)
        )
        
        # Apply date filters
        if parsed_start_date:
            query = query.filter(Transaction.transaction_date >= parsed_start_date)
        
        if parsed_end_date:
            query = query.filter(Transaction.transaction_date <= parsed_end_date)
        
        # Group by category (NULL group represents Uncategorized)
        query = query.group_by(Category.id, Category.name)
        
        # Execute query
        results = query.all()
        
        # Calculate total for percentage calculation
        total_amount_cents = sum(abs(result.total_amount_cents) for result in results if result.total_amount_cents)
        
        # Format results
        breakdown = []
        for result in results:
            total_amount_dollars = result.total_amount_cents / 100 if result.total_amount_cents else 0
            percentage = (abs(result.total_amount_cents) / total_amount_cents * 100) if total_amount_cents > 0 else 0
            
            breakdown.append({
                "category_id": result.category_id,
                "category_name": result.category_name,
                "total_amount": total_amount_dollars,
                "transaction_count": result.transaction_count,
                "percentage": round(percentage, 2)
            })
        
        # Sort by absolute amount descending
        breakdown.sort(key=lambda x: abs(x["total_amount"]), reverse=True)
        
        logger.info(f"Generated category breakdown for user {current_user.id}: {len(breakdown)} categories")
        return breakdown
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get category breakdown for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve category breakdown"
        )


@router.get("/net-worth-trend")
async def get_net_worth_trend(
    period: str = Query("90d", description="Time period: 90d, 1y, or all"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get net worth trend data for the specified period"""
    try:
        # Calculate date range based on period
        end_date = datetime.now().date()
        
        if period == "90d":
            start_date = end_date - timedelta(days=90)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "all":
            # Get the earliest transaction date for the user
            earliest_transaction = db.query(Transaction).filter(
                Transaction.user_id == current_user.id
            ).order_by(Transaction.transaction_date.asc()).first()
            
            if earliest_transaction:
                start_date = earliest_transaction.transaction_date
            else:
                start_date = end_date - timedelta(days=365)  # Default to 1 year if no transactions
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid period. Use '90d', '1y', or 'all'"
            )
        
        # Get all user accounts
        accounts = db.query(Account).filter(
            Account.user_id == current_user.id,
            Account.is_active == True
        ).all()
        
        if not accounts:
            return []
        
        net_worth_data = []
        current_net_worth = 0

        for account in accounts:
            balance = account.balance_cents / 100  # Convert to dollars
            
            # Add positive balances from checking, savings, investment accounts
            if account.account_type in ['checking', 'savings', 'investment', 'retirement']:
                if balance > 0:
                    current_net_worth += balance
            # Subtract debt from credit cards and loans
            elif account.account_type in ['credit_card', 'loan']:
                if balance < 0:
                    current_net_worth += balance  # balance is already negative
        
        current_date = start_date
        days_diff = (end_date - start_date).days
        
        # Generate daily data points (simplified for demo)
        interval = max(1, days_diff // 30)  # Show about 30 data points max
        
        while current_date <= end_date:
            net_worth_data.append({
                "date": current_date.isoformat(),
                "net_worth": current_net_worth
            })
            current_date += timedelta(days=interval)
        
        # Ensure we include the current date
        if net_worth_data and net_worth_data[-1]["date"] != end_date.isoformat():
            net_worth_data.append({
                "date": end_date.isoformat(),
                "net_worth": current_net_worth
            })
        
        logger.info(f"Generated net worth trend data for user {current_user.id}: {len(net_worth_data)} points")
        return net_worth_data
        
    except Exception as e:
        logger.error(f"Failed to get net worth trend for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve net worth trend data"
        )


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get dashboard summary including net worth, account totals, and financial health"""
    try:
        # Calculate user financial health
        health_service = get_financial_health_service()
        financial_health = health_service.calculate_user_financial_health(db, current_user.id)
        
        # Get recent transactions count
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= thirty_days_ago.date()
        ).count()
        
        # Get account count
        account_count = db.query(Account).filter(
            Account.user_id == current_user.id,
            Account.is_active == True
        ).count()
        
        return {
            "net_worth": financial_health.get("net_worth", 0),
            "total_liquid": financial_health.get("total_liquid", 0),
            "total_debt": financial_health.get("total_debt", 0),
            "total_investment": financial_health.get("total_investment", 0),
            "financial_health_score": financial_health.get("overall_score", 0),
            "financial_health_grade": financial_health.get("grade", "N/A"),
            "account_count": account_count,
            "recent_transactions": recent_transactions,
            "recommendations": financial_health.get("recommendations", []),
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard summary"
        )
