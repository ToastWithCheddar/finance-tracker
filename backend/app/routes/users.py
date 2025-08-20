from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import uuid
import logging

from app.database import get_db
from app.dependencies import get_user_service
from app.auth.dependencies import get_current_user, get_current_active_user, get_db_with_user_context
from app.schemas.user import UserResponse, UserUpdate, UserProfile
from app.schemas.user_session import UserSessionPublic, SessionStatsResponse
from app.services.user_service import UserService
from app.models.user import User
from app.core.exceptions import (
    DataIntegrityError,
    ResourceNotFoundError,
    ValidationError
)

router = APIRouter()
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
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
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
        logger.error(f"Database error updating user profile: {str(e)}", exc_info=True)
        raise DataIntegrityError("Failed to update user profile due to database error")
    except Exception as e:
        logger.error(f"Unexpected error updating user profile: {str(e)}", exc_info=True)
        raise DataIntegrityError("Failed to update user profile")

@router.delete("/me")
async def delete_current_user_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
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
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
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
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID (public profile)"""
    user = user_service.get(db=db, id=user_id)
    if not user:
        raise ResourceNotFoundError("User", str(user_id))
    return user



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

# Session Management Endpoints
@router.get("/me/sessions", response_model=List[UserSessionPublic])
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
):
    """Get all active sessions for the current user"""
    try:
        sessions = user_service.get_user_sessions(db, current_user.id)
        
        # Convert sessions to public format and identify current session
        session_list = []
        for session in sessions:
            session_data = UserSessionPublic.from_orm(session)
            # You'd need to determine current session based on the JWT token
            # For now, we'll mark the most recent as current (this is simplified)
            session_data.is_current = session == sessions[0] if sessions else False
            session_list.append(session_data)
        
        return session_list
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}", exc_info=True)
        raise DataIntegrityError("Failed to retrieve user sessions")

@router.get("/me/sessions/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
):
    """Get session statistics for the current user"""
    try:
        stats = user_service.get_session_stats(db, current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}", exc_info=True)
        raise DataIntegrityError("Failed to retrieve session statistics")

@router.delete("/me/sessions/{session_id}")
async def revoke_user_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
):
    """Revoke a specific user session"""
    try:
        success = user_service.revoke_session(db, current_user.id, session_id)
        if not success:
            raise ResourceNotFoundError("Session", str(session_id))
        return {"message": "Session revoked successfully"}
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke session {session_id}: {e}", exc_info=True)
        raise DataIntegrityError("Failed to revoke session")

@router.post("/me/sessions/revoke-all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    user_service: UserService = Depends(get_user_service)
):
    """Revoke all other sessions except the current one"""
    try:
        revoked_count = user_service.revoke_all_other_sessions(db, current_user.id)
        return {
            "message": f"Successfully revoked {revoked_count} session(s)",
            "revoked_sessions": revoked_count
        }
    except Exception as e:
        logger.error(f"Failed to revoke all sessions: {e}", exc_info=True)
        raise DataIntegrityError("Failed to revoke sessions")

