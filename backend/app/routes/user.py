from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import uuid
import logging

from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_active_user
from app.schemas.user import UserResponse, UserUpdate, UserProfile
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.user_service import UserService
from app.services.user_preferences_service import UserPreferencesService
from app.models.user import User

router = APIRouter()
user_service = UserService()
preferences_service = UserPreferencesService()
logger = logging.getLogger(__name__)

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    try:
        updated_user = user_service.update(
            db=db,
            db_obj=current_user,
            obj_in=user_update
        )
        return updated_user
    except SQLAlchemyError as e:
        logger.error(f"Database error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )

@router.delete("/me")
async def delete_current_user_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete current user's account"""
    user_service.deactivate_user(db=db, user_id=current_user.id)
    return {"message": "Account deactivated successfully"}

@router.get("/search", response_model=List[UserProfile])
async def search_users(
    query: str = Query(..., min_length=3),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users (for admin or specific features)"""
    users = user_service.search_users(
        db=db,
        query=query,
        skip=skip,
        limit=limit
    )
    return users

@router.get("/{user_id}", response_model=UserProfile)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (public profile)"""
    user = user_service.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# User Preferences Endpoints
@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's preferences"""
    preferences = preferences_service.get_or_create_preferences(db, current_user.id)
    return preferences

@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's preferences"""
    updated_preferences = preferences_service.update_user_preferences(
        db, current_user.id, preferences_update
    )
    return updated_preferences

@router.post("/me/preferences/reset", response_model=UserPreferencesResponse)
async def reset_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset user preferences to default values"""
    default_preferences = preferences_service.reset_to_defaults(db, current_user.id)
    return default_preferences

# Enhanced User Profile
@router.get("/me/profile", response_model=UserProfile)
async def get_detailed_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's public profile information (safe for sharing)"""
    # Return only public-safe fields as defined in UserProfile schema
    return UserProfile(
        id=current_user.id,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url
    )