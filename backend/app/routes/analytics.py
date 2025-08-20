from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional
from uuid import UUID
import logging

from app.core.exceptions import ValidationError, BusinessLogicError

from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.database import get_db
from app.models.user import User
from app.services.analytics_service import analytics_service
from app.services.transaction_service import TransactionService
from app.schemas.timeline_annotation import TimelineEventsList

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_analytics(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get aggregated analytics data for the main dashboard.
    """
    analytics_data = await analytics_service.get_dashboard_summary(db, current_user.id)
    return {"success": True, "data": analytics_data}


@router.get("/money-flow")
async def get_money_flow(
    start_date: date = Query(..., description="Start date for money flow analysis (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for money flow analysis (YYYY-MM-DD)"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get money flow data for Sankey diagram visualization.
    
    Returns nodes and links structure showing how money flows from income sources
    through total income to expense categories and savings.
    """
    try:
        # Validate date range
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")
        
        # Validate date range isn't too large (max 1 year)
        if (end_date - start_date).days > 365:
            raise ValidationError("Date range cannot exceed 365 days")
        
        flow_data = await analytics_service.get_money_flow_data(db, current_user.id, start_date, end_date)
        
        # Check if there's any data to show
        if not flow_data.get("links") or len(flow_data["links"]) == 0:
            return {
                "success": True,
                "data": flow_data,
                "message": "No transaction data available for the selected period"
            }
        
        return {"success": True, "data": flow_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get money flow data for user {current_user.id}: {e}", exc_info=True)
        raise BusinessLogicError("Could not process money flow data")


@router.get("/spending-heatmap")
async def get_spending_heatmap(
    start_date: date = Query(..., description="Start date for spending heatmap (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for spending heatmap (YYYY-MM-DD)"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get daily spending data for calendar heatmap visualization.
    
    Returns array of objects with 'day' (ISO date string) and 'value' (amount in cents)
    suitable for Nivo Calendar component.
    """
    try:
        # Validate date range
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")
        
        # Validate date range isn't too large (max 366 days for leap year)
        if (end_date - start_date).days > 366:
            raise ValidationError("Date range cannot exceed one year")
        
        heatmap_data = await analytics_service.get_spending_heatmap_data(db, current_user.id, start_date, end_date)
        
        return {"success": True, "data": heatmap_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get spending heatmap data for user {current_user.id}: {e}", exc_info=True)
        raise BusinessLogicError("Could not process spending heatmap data")


@router.get("/timeline", response_model=TimelineEventsList)
async def get_financial_timeline(
    start_date: date = Query(..., description="Start date for timeline (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for timeline (YYYY-MM-DD)"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get financial timeline events combining annotations, goals, and significant transactions.
    
    Returns a chronological view of important financial events including:
    - User-created timeline annotations
    - Goal creation and completion events
    - Significant transactions (over $500)
    """
    try:
        # Validate date range
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")
        
        # Validate date range isn't too large (max 2 years)
        if (end_date - start_date).days > 730:
            raise ValidationError("Date range cannot exceed 2 years")
        
        timeline_data = await analytics_service.get_financial_timeline(
            db, current_user.id, start_date, end_date
        )
        
        return TimelineEventsList(
            events=timeline_data["events"],
            total_count=timeline_data["total_count"],
            start_date=timeline_data["start_date"],
            end_date=timeline_data["end_date"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get financial timeline for user {current_user.id}: {e}", exc_info=True)
        raise BusinessLogicError("Could not process financial timeline data")


@router.get("/net-worth-trend")
async def get_net_worth_trend(
    period: str = Query(default="90d", description="Time period: '90d', '1y', or 'all'"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get net worth trend data for line chart visualization.
    
    Returns array of data points with date and net worth values.
    Period options:
    - '90d': Last 90 days with weekly data points
    - '1y': Last year with monthly data points  
    - 'all': All available data with adaptive intervals
    """
    try:
        # Validate period parameter
        valid_periods = ['90d', '1y', 'all']
        if period not in valid_periods:
            raise ValidationError(f"Invalid period. Must be one of: {', '.join(valid_periods)}")
        
        trend_data = await analytics_service.get_net_worth_trend(db, current_user.id, period)
        
        # Check if there's any data to show
        if not trend_data:
            return {
                "success": True,
                "data": [],
                "message": "No account data available for net worth calculation"
            }
        
        return {"success": True, "data": trend_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get net worth trend for user {current_user.id}: {e}", exc_info=True)
        raise BusinessLogicError("Could not process net worth trend data")


@router.get("/cash-flow-waterfall")
async def get_cash_flow_waterfall(
    start_date: date = Query(..., description="Start date for cash flow analysis (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for cash flow analysis (YYYY-MM-DD)"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get cash flow waterfall data showing balance changes over a period.
    
    Returns data structure with starting balance, income, expenses, and ending balance
    suitable for waterfall chart visualization.
    """
    try:
        # Validate date range
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")
        
        # Validate date range isn't too large (max 1 year)
        if (end_date - start_date).days > 365:
            raise ValidationError("Date range cannot exceed 365 days")
        
        waterfall_data = await analytics_service.get_cash_flow_waterfall(
            db, current_user.id, start_date, end_date
        )
        
        return {"success": True, "data": waterfall_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cash flow waterfall for user {current_user.id}: {e}", exc_info=True)
        raise BusinessLogicError("Could not process cash flow waterfall data")


# Transaction-specific analytics endpoints moved from transactions router
@router.get("/transaction-stats")
def get_transaction_stats(
    start_date: Optional[date] = Query(None, description="Start date for stats period"),
    end_date: Optional[date] = Query(None, description="End date for stats period"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    search_query: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """Get transaction summary statistics"""
    return TransactionService.get_transaction_summary(db, current_user.id, start_date, end_date, category_id, search_query)

@router.get("/transaction-dashboard")
def get_transaction_dashboard_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics period"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive transaction dashboard analytics for the current user"""
    return TransactionService.get_dashboard_analytics(db, current_user.id, start_date, end_date)

@router.get("/spending-trends")
def get_spending_trends(
    period: str = Query("monthly", pattern="^(weekly|monthly)$", description="Trend period"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_active_user)
):
    """Get spending trends over time"""
    return TransactionService.get_spending_trends(db, current_user.id, period)