from typing import Optional
from sqlalchemy.orm import Session
import uuid

from app.models.user_preferences import UserPreferences
from app.schemas.user_preferences import UserPreferencesCreate, UserPreferencesUpdate
from .base_service import BaseService

class UserPreferencesService(BaseService[UserPreferences, UserPreferencesCreate, UserPreferencesUpdate]):
    def __init__(self):
        super().__init__(UserPreferences)
    
    def get_by_user_id(self, db: Session, user_id: uuid.UUID) -> Optional[UserPreferences]:
        """Get user preferences by user ID"""
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).first()
    
    def create_default_preferences(self, db: Session, user_id: uuid.UUID) -> UserPreferences:
        """Create default preferences for a new user"""
        preferences_data = UserPreferencesCreate()
        db_preferences = UserPreferences(
            user_id=user_id,
            **preferences_data.model_dump()
        )
        db.add(db_preferences)
        db.commit()
        db.refresh(db_preferences)
        return db_preferences
    
    def get_or_create_preferences(self, db: Session, user_id: uuid.UUID) -> UserPreferences:
        """Get user preferences or create default ones if they don't exist"""
        preferences = self.get_by_user_id(db, user_id)
        if not preferences:
            preferences = self.create_default_preferences(db, user_id)
        return preferences
    
    def update_user_preferences(
        self, 
        db: Session, 
        user_id: uuid.UUID, 
        preferences_update: UserPreferencesUpdate
    ) -> Optional[UserPreferences]:
        """Update user preferences"""
        db_preferences = self.get_by_user_id(db, user_id)
        if not db_preferences:
            # Create preferences if they don't exist
            db_preferences = self.create_default_preferences(db, user_id)
        
        return self.update(db=db, db_obj=db_preferences, obj_in=preferences_update)
    
    def reset_to_defaults(self, db: Session, user_id: uuid.UUID) -> UserPreferences:
        """Reset user preferences to default values"""
        db_preferences = self.get_by_user_id(db, user_id)
        if db_preferences:
            # Delete existing preferences
            db.delete(db_preferences)
            db.commit()
        
        # Create new default preferences
        return self.create_default_preferences(db, user_id)