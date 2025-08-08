from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from .base_service import BaseService

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