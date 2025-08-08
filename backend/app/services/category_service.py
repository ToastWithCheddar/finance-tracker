from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid

from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate, CategoryUpdate
from .base_service import BaseService

class CategoryService(BaseService[Category, CategoryCreate, CategoryUpdate]):
    def __init__(self):
        super().__init__(Category)
    
    def get_categories(
        self, 
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[uuid.UUID] = None,
        include_system: bool = True,
        parent_only: bool = False,
        search: Optional[str] = None
    ) -> List[Category]:
        """Get categories with various filters"""
        query = db.query(self.model)
        
        # Filter by user and system categories
        if user_id and include_system:
            query = query.filter(
                or_(
                    self.model.user_id == user_id,
                    self.model.is_system == True
                )
            )
        elif user_id:
            query = query.filter(self.model.user_id == user_id)
        elif include_system:
            query = query.filter(self.model.is_system == True)
        
        # Filter parent categories only
        if parent_only:
            query = query.filter(self.model.parent_id.is_(None))
        
        # Search filter
        if search:
            query = query.filter(
                or_(
                    self.model.name.ilike(f"%{search}%"),
                    self.model.description.ilike(f"%{search}%")
                )
            )
        
        # Filter only active categories
        query = query.filter(self.model.is_active == True)
        
        # Order by sort_order and name
        query = query.order_by(self.model.sort_order, self.model.name)
        
        return query.offset(skip).limit(limit).all()
    
    def get_system_categories(self, db: Session) -> List[Category]:
        """Get all system categories"""
        return db.query(self.model).filter(
            and_(
                self.model.is_system == True,
                self.model.is_active == True
            )
        ).order_by(self.model.sort_order, self.model.name).all()
    
    def get_user_categories(
        self, 
        db: Session, 
        user_id: uuid.UUID,
        include_system: bool = True
    ) -> List[Category]:
        """Get all categories for a specific user (custom + system)"""
        query = db.query(self.model)
        
        if include_system:
            query = query.filter(
                or_(
                    self.model.user_id == user_id,
                    self.model.is_system == True
                )
            )
        else:
            query = query.filter(self.model.user_id == user_id)
        
        return query.filter(self.model.is_active == True).order_by(
            self.model.sort_order, self.model.name
        ).all()
    
    def get_by_name(
        self, 
        db: Session, 
        name: str, 
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[Category]:
        """Get category by name"""
        query = db.query(self.model).filter(
            and_(
                self.model.name == name,
                self.model.is_active == True
            )
        )
        
        if user_id:
            query = query.filter(
                or_(
                    self.model.user_id == user_id,
                    self.model.is_system == True
                )
            )
        else:
            query = query.filter(self.model.is_system == True)
        
        return query.first()
    
    def has_transactions(self, db: Session, category_id: uuid.UUID) -> bool:
        """Check if category has any transactions"""
        return db.query(Transaction).filter(
            Transaction.category_id == category_id
        ).first() is not None
    
    def get_category_stats(self, db: Session, category_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """Get category usage statistics"""
        transaction_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.category_id == category_id,
                Transaction.user_id == user_id
            )
        ).scalar()
        
        total_amount = db.query(func.sum(Transaction.amount_cents)).filter(
            and_(
                Transaction.category_id == category_id,
                Transaction.user_id == user_id
            )
        ).scalar() or 0
        
        return {
            "transaction_count": transaction_count,
            "total_amount_cents": total_amount
        }
    
    def build_hierarchy(self, categories: List[Category]) -> List[Category]:
        """Build hierarchical structure from flat category list"""
        category_map = {}
        root_categories = []
        
        # First pass: create category map
        for category in categories:
            category_map[category.id] = category
            # Initialize children list if not exists
            if not hasattr(category, 'children'):
                category.children = []
        
        # Second pass: build hierarchy
        for category in categories:
            if category.parent_id:
                parent = category_map.get(category.parent_id)
                if parent:
                    if not hasattr(parent, 'children'):
                        parent.children = []
                    parent.children.append(category)
                else:
                    # Parent not found, treat as root
                    root_categories.append(category)
            else:
                root_categories.append(category)
        
        # Sort categories by sort_order and name
        def sort_categories(cats):
            cats.sort(key=lambda x: (x.sort_order, x.name))
            for cat in cats:
                if hasattr(cat, 'children') and cat.children:
                    sort_categories(cat.children)
        
        sort_categories(root_categories)
        return root_categories