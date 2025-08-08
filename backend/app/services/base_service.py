from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
from app.models.base import BaseModel as SQLBaseModel
import uuid

ModelType = TypeVar("ModelType", bound=SQLBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Get single record by ID"""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[uuid.UUID] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple records with optional filtering"""
        query = db.query(self.model)
        
        # Apply user filter if model has user_id
        if user_id and hasattr(self.model, 'user_id'):
            query = query.filter(self.model.user_id == user_id)
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType, user_id: Optional[uuid.UUID] = None) -> ModelType:
        """Create new record"""
        obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        
        # Add user_id if model supports it
        if user_id and hasattr(self.model, 'user_id'):
            obj_in_data['user_id'] = user_id
        
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Update existing record"""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
        
        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Delete record by ID"""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def count(self, db: Session, *, user_id: Optional[uuid.UUID] = None) -> int:
        """Count records"""
        query = db.query(self.model)
        if user_id and hasattr(self.model, 'user_id'):
            query = query.filter(self.model.user_id == user_id)
        return query.count()
    
    def exists(self, db: Session, *, id: Any) -> bool:
        """Check if record exists"""
        return db.query(self.model).filter(self.model.id == id).first() is not None