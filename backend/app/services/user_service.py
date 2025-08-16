from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid
import logging

from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.user_session import UserSessionCreate, UserSessionUpdate, SessionStatsResponse
from .base_service import BaseService

logger = logging.getLogger(__name__)

class UserService(BaseService[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email address"""
        return db.query(self.model).filter(
            and_(
                self.model.email == email,
                self.model.is_active == True
            )
        ).first()
    
    def get_by_supabase_id(self, db: Session, supabase_user_id: uuid.UUID) -> Optional[User]:
        """Get user by Supabase user ID"""
        return db.query(self.model).filter(
            and_(
                self.model.supabase_user_id == supabase_user_id,
                self.model.is_active == True
            )
        ).first()
    
    def get_active_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all active users"""
        return db.query(self.model).filter(
            self.model.is_active == True
        ).offset(skip).limit(limit).all()
    
    def create_user(self, db: Session, user_create: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = self.get_by_email(db=db, email=user_create.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        return self.create(db=db, obj_in=user_create)
    
    def update_user(self, db: Session, user_id: uuid.UUID, user_update: UserUpdate) -> Optional[User]:
        """Update user information"""
        db_user = self.get(db=db, id=user_id)
        if not db_user:
            return None
        
        return self.update(db=db, db_obj=db_user, obj_in=user_update)
    
    def deactivate_user(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Deactivate a user account"""
        db_user = self.get(db=db, id=user_id)
        if not db_user:
            return None
        
        user_update = UserUpdate(is_active=False)
        return self.update(db=db, db_obj=db_user, obj_in=user_update)
    
    def verify_user_email(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Mark user email as verified"""
        db_user = self.get(db=db, id=user_id)
        if not db_user:
            return None
        
        from datetime import datetime
        user_update = UserUpdate(
            is_verified=True,
            email_verified_at=datetime.utcnow()
        )
        return self.update(db=db, db_obj=db_user, obj_in=user_update)
    
    def search_users(self, db: Session, query: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by name or email"""
        return db.query(self.model).filter(
            and_(
                self.model.is_active == True,
                or_(
                    self.model.email.ilike(f"%{query}%"),
                    self.model.display_name.ilike(f"%{query}%"),
                    self.model.first_name.ilike(f"%{query}%"),
                    self.model.last_name.ilike(f"%{query}%")
                )
            )
        ).offset(skip).limit(limit).all()

    def update_user_from_webhook(self, db: Session, supabase_user_id: uuid.UUID, data: Dict[str, Any]) -> Optional[User]:
        """Updates a user's details based on a webhook payload."""
        db_user = self.get_by_supabase_id(db, supabase_user_id)
        if not db_user:
            # User might not exist locally yet, which is a possible edge case.
            # For now, we'll just log it. A more advanced implementation might create the user.
            logger.warning(f"Webhook for non-existent user received: {supabase_user_id}")
            return None

        # Map relevant fields from the webhook payload to our UserUpdate schema
        update_data = UserUpdate(
            email=data.get("email"),
            display_name=data.get("user_metadata", {}).get("display_name") if data.get("user_metadata") else None,
            first_name=data.get("user_metadata", {}).get("first_name") if data.get("user_metadata") else None,
            last_name=data.get("user_metadata", {}).get("last_name") if data.get("user_metadata") else None,
            is_verified=data.get("email_confirmed_at") is not None
        )
        
        try:
            return self.update(db=db, db_obj=db_user, obj_in=update_data)
        except Exception as e:
            logger.error(f"Failed to update user from webhook: {e}")
            return None

    def delete_user_by_supabase_id(self, db: Session, supabase_user_id: uuid.UUID) -> Optional[User]:
        """Deactivates a user based on a webhook delete event."""
        db_user = self.get_by_supabase_id(db, supabase_user_id)
        if not db_user:
            logger.warning(f"Webhook for deletion of non-existent user received: {supabase_user_id}")
            return None

        # We will perform a soft delete by deactivating the user.
        try:
            return self.deactivate_user(db=db, user_id=db_user.id)
        except Exception as e:
            logger.error(f"Failed to deactivate user from webhook: {e}")
            return None

    # Session Management Methods
    def create_user_session(
        self, 
        db: Session, 
        user_id: uuid.UUID, 
        session_data: UserSessionCreate
    ) -> UserSession:
        """Create a new user session"""
        session = UserSession(
            user_id=user_id,
            session_token=session_data.session_token,
            device_info=session_data.device_info,
            user_agent=session_data.user_agent,
            ip_address=session_data.ip_address,
            location=session_data.location,
            expires_at=session_data.expires_at
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def get_user_sessions(self, db: Session, user_id: uuid.UUID, include_inactive: bool = False) -> List[UserSession]:
        """Get all sessions for a user"""
        query = db.query(UserSession).filter(UserSession.user_id == user_id)
        
        if not include_inactive:
            query = query.filter(UserSession.is_active == True)
        
        return query.order_by(UserSession.last_activity.desc()).all()

    def get_session_by_token(self, db: Session, session_token: str) -> Optional[UserSession]:
        """Get session by token"""
        return db.query(UserSession).filter(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True
            )
        ).first()

    def update_session_activity(self, db: Session, session_token: str) -> bool:
        """Update session last activity timestamp"""
        session = self.get_session_by_token(db, session_token)
        if not session:
            return False
        
        session.last_activity = datetime.utcnow()
        db.commit()
        return True

    def revoke_session(self, db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        """Revoke a specific user session"""
        session = db.query(UserSession).filter(
            and_(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).first()
        
        if not session:
            return False
        
        session.is_active = False
        db.commit()
        return True

    def revoke_all_other_sessions(self, db: Session, user_id: uuid.UUID, keep_session_token: Optional[str] = None) -> int:
        """Revoke all sessions for a user except optionally one to keep"""
        query = db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        
        if keep_session_token:
            query = query.filter(UserSession.session_token != keep_session_token)
        
        sessions = query.all()
        count = len(sessions)
        
        for session in sessions:
            session.is_active = False
        
        db.commit()
        return count

    def cleanup_expired_sessions(self, db: Session) -> int:
        """Clean up expired sessions (utility method)"""
        expired_sessions = db.query(UserSession).filter(
            and_(
                UserSession.expires_at < datetime.utcnow(),
                UserSession.is_active == True
            )
        ).all()
        
        count = len(expired_sessions)
        for session in expired_sessions:
            session.is_active = False
        
        db.commit()
        return count

    def get_session_stats(self, db: Session, user_id: uuid.UUID) -> SessionStatsResponse:
        """Get session statistics for a user"""
        total_sessions = db.query(func.count(UserSession.id)).filter(
            UserSession.user_id == user_id
        ).scalar()
        
        active_sessions = db.query(func.count(UserSession.id)).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).scalar()
        
        inactive_sessions = total_sessions - active_sessions
        
        # Get most recent active session as "current"
        current_session = db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).order_by(UserSession.last_activity.desc()).first()
        
        return SessionStatsResponse(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            inactive_sessions=inactive_sessions,
            current_session_id=current_session.id if current_session else None
        )