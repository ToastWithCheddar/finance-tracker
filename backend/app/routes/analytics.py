from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database.session import get_db
from app.models.user import User
from app.services.analytics_service import analytics_service

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get aggregated analytics data for the main dashboard.
    """
    analytics_data = await analytics_service.get_dashboard_summary(db, current_user.id)
    return {"success": True, "data": analytics_data}