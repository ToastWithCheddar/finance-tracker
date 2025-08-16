from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from ..database import get_db
from ..models.saved_filter import SavedFilter
from ..schemas.saved_filter import SavedFilterCreate, SavedFilterUpdate, SavedFilterResponse
from ..auth.dependencies import get_current_user, get_db_with_user_context
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["saved-filters"])


@router.post("", response_model=SavedFilterResponse)
async def create_saved_filter(
    saved_filter: SavedFilterCreate,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Create a new saved filter for the current user."""
    try:
        # Check if user already has a filter with this name
        existing_filter = db.query(SavedFilter).filter(
            SavedFilter.user_id == current_user.id,
            SavedFilter.name == saved_filter.name
        ).first()
        
        if existing_filter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A saved filter with this name already exists"
            )
        
        # Create new saved filter
        db_saved_filter = SavedFilter(
            user_id=current_user.id,
            name=saved_filter.name,
            filters=saved_filter.filters
        )
        
        db.add(db_saved_filter)
        db.commit()
        db.refresh(db_saved_filter)
        
        logger.info(f"Created saved filter '{saved_filter.name}' for user {current_user.id}")
        return db_saved_filter
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create saved filter"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create saved filter"
        )


@router.get("", response_model=List[SavedFilterResponse])
async def get_saved_filters(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get all saved filters for the current user."""
    try:
        saved_filters = db.query(SavedFilter).filter(
            SavedFilter.user_id == current_user.id
        ).order_by(SavedFilter.created_at.desc()).all()
        
        return saved_filters
        
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching saved filters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved filters"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching saved filters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved filters"
        )


@router.get("/{filter_id}", response_model=SavedFilterResponse)
async def get_saved_filter(
    filter_id: UUID,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get a specific saved filter by ID."""
    try:
        saved_filter = db.query(SavedFilter).filter(
            SavedFilter.id == filter_id,
            SavedFilter.user_id == current_user.id
        ).first()
        
        if not saved_filter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved filter not found"
            )
        
        return saved_filter
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved filter"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved filter"
        )


@router.put("/{filter_id}", response_model=SavedFilterResponse)
async def update_saved_filter(
    filter_id: UUID,
    saved_filter_update: SavedFilterUpdate,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Update an existing saved filter."""
    try:
        # Get the saved filter
        saved_filter = db.query(SavedFilter).filter(
            SavedFilter.id == filter_id,
            SavedFilter.user_id == current_user.id
        ).first()
        
        if not saved_filter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved filter not found"
            )
        
        # Check if name is being changed and if it conflicts
        if (saved_filter_update.name and 
            saved_filter_update.name != saved_filter.name):
            existing_filter = db.query(SavedFilter).filter(
                SavedFilter.user_id == current_user.id,
                SavedFilter.name == saved_filter_update.name,
                SavedFilter.id != filter_id
            ).first()
            
            if existing_filter:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A saved filter with this name already exists"
                )
        
        # Update the saved filter
        update_data = saved_filter_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(saved_filter, key, value)
        
        db.commit()
        db.refresh(saved_filter)
        
        logger.info(f"Updated saved filter {filter_id} for user {current_user.id}")
        return saved_filter
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update saved filter"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update saved filter"
        )


@router.delete("/{filter_id}")
async def delete_saved_filter(
    filter_id: UUID,
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Delete a saved filter."""
    try:
        # Get the saved filter
        saved_filter = db.query(SavedFilter).filter(
            SavedFilter.id == filter_id,
            SavedFilter.user_id == current_user.id
        ).first()
        
        if not saved_filter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved filter not found"
            )
        
        # Delete the saved filter
        db.delete(saved_filter)
        db.commit()
        
        logger.info(f"Deleted saved filter {filter_id} for user {current_user.id}")
        return {"message": "Saved filter deleted successfully"}
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved filter"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting saved filter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved filter"
        )