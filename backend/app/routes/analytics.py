from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
import logging

from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.database import get_db
from app.models.user import User
from app.services.analytics_service import analytics_service
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
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Validate date range isn't too large (max 1 year)
        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")
        
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
        raise HTTPException(status_code=500, detail="Could not process money flow data")


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
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Validate date range isn't too large (max 366 days for leap year)
        if (end_date - start_date).days > 366:
            raise HTTPException(status_code=400, detail="Date range cannot exceed one year")
        
        heatmap_data = await analytics_service.get_spending_heatmap_data(db, current_user.id, start_date, end_date)
        
        return {"success": True, "data": heatmap_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get spending heatmap data for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not process spending heatmap data")


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
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Validate date range isn't too large (max 2 years)
        if (end_date - start_date).days > 730:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 2 years")
        
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
        raise HTTPException(status_code=500, detail="Could not process financial timeline data")