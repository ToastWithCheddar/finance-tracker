from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
import logging

from ..database import get_db
from ..schemas.insight import (
    InsightResponse, InsightUpdate, InsightListResponse, 
    InsightFilter, InsightType, InsightPriority
)
from ..auth.dependencies import get_current_user, get_db_with_user_context
from ..models.user import User
from ..models.insight import Insight

router = APIRouter(tags=["insights"])
logger = logging.getLogger(__name__)


@router.get("", response_model=InsightListResponse)
def get_insights(
    type: Optional[InsightType] = Query(None, description="Filter by insight type"),
    priority: Optional[InsightPriority] = Query(None, description="Filter by priority"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    limit: int = Query(30, ge=1, le=100, description="Number of insights to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get insights with optional filters"""
    try:
        # Build query
        query = db.query(Insight).filter(Insight.user_id == current_user.id)
        
        # Apply filters
        if type:
            query = query.filter(Insight.type == type.value)
        if priority:
            query = query.filter(Insight.priority == priority.value)
        if is_read is not None:
            query = query.filter(Insight.is_read == is_read)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Get unread count
        unread_count = db.query(Insight).filter(
            Insight.user_id == current_user.id,
            Insight.is_read == False
        ).count()
        
        # Apply pagination and ordering (most recent first)
        insights = query.order_by(Insight.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to response models
        insight_responses = []
        for insight in insights:
            insight_responses.append(InsightResponse(
                id=insight.id,
                user_id=insight.user_id,
                transaction_id=insight.transaction_id,
                type=insight.type,
                title=insight.title,
                description=insight.description,
                priority=insight.priority,
                is_read=insight.is_read,
                extra_payload=insight.extra_payload,
                created_at=insight.created_at,
                updated_at=insight.updated_at
            ))
        
        return InsightListResponse(
            insights=insight_responses,
            total_count=total_count,
            unread_count=unread_count
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting insights: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve insights due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting insights: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve insights"
        )


@router.patch("/{insight_id}", response_model=InsightResponse)
def update_insight(
    insight_id: UUID,
    insight_update: InsightUpdate,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Update an insight (primarily for marking as read/unread)"""
    try:
        # Get insight
        insight = db.query(Insight).filter(
            Insight.id == insight_id,
            Insight.user_id == current_user.id
        ).first()
        
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insight not found"
            )
        
        # Update insight
        if insight_update.is_read is not None:
            insight.is_read = insight_update.is_read
        
        db.commit()
        db.refresh(insight)
        
        return InsightResponse(
            id=insight.id,
            user_id=insight.user_id,
            transaction_id=insight.transaction_id,
            type=insight.type,
            title=insight.title,
            description=insight.description,
            priority=insight.priority,
            is_read=insight.is_read,
            extra_payload=insight.extra_payload,
            created_at=insight.created_at,
            updated_at=insight.updated_at
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error updating insight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update insight due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating insight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update insight"
        )


@router.delete("/{insight_id}")
def delete_insight(
    insight_id: UUID,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Delete an insight"""
    try:
        # Get insight
        insight = db.query(Insight).filter(
            Insight.id == insight_id,
            Insight.user_id == current_user.id
        ).first()
        
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insight not found"
            )
        
        db.delete(insight)
        db.commit()
        
        return {"message": "Insight deleted successfully"}
        
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting insight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete insight due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting insight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete insight"
        )