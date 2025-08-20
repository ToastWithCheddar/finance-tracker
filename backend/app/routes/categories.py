from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database import get_db
from app.auth.dependencies import get_current_user, get_optional_user, get_db_with_user_context
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.dependencies import get_category_service
from app.services.category_service import CategoryService

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_system: bool = Query(True),
    parent_only: bool = Query(False),
    search: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db_with_user_context),
    category_service: CategoryService = Depends(get_category_service)
):
    """Get all categories (system + user's custom categories)"""
    categories = category_service.get_categories(
        db=db,
        skip=skip,
        limit=limit,
        user_id=current_user.id if current_user else None,
        include_system=include_system,
        parent_only=parent_only,
        search=search
    )
    return categories

@router.get("/system", response_model=List[CategoryResponse])
async def get_system_categories(
    db: Session = Depends(get_db),
    category_service: CategoryService = Depends(get_category_service)
):
    """Get all system (default) categories"""
    return category_service.get_system_categories(db=db)

@router.get("/my", response_model=List[CategoryResponse])
async def get_my_categories(
    include_system: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get current user's categories"""
    return category_service.get_user_categories(
        db=db,
        user_id=current_user.id,
        include_system=include_system
    )

@router.get("/hierarchy", response_model=List[CategoryResponse])
async def get_categories_hierarchy(
    include_system: bool = Query(True),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get categories organized in hierarchical structure"""
    categories = category_service.get_categories(
        db=db,
        skip=0,
        limit=1000,
        user_id=current_user.id if current_user else None,
        include_system=include_system,
        parent_only=False,
        search=None
    )
    
    # Build hierarchy server-side for better performance
    return category_service.build_hierarchy(categories)

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Get a specific category by ID"""
    category = category_service.get(db=db, id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if user has access to this category
    if category.user_id and current_user and category.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return category

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Create a new custom category"""
    # Check if category name already exists for user
    existing_category = category_service.get_by_name(
        db=db,
        name=category.name,
        user_id=current_user.id
    )
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    return category_service.create(
        db=db,
        obj_in=category,
        user_id=current_user.id
    )

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    category: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Update a custom category"""
    db_category = category_service.get(db=db, id=category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Only allow updating user's own categories
    if db_category.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this category"
        )
    
    # Don't allow updating system categories
    if db_category.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system categories"
        )
    
    return category_service.update(
        db=db,
        db_obj=db_category,
        obj_in=category
    )

@router.delete("/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_user_context)
):
    """Delete a custom category"""
    db_category = category_service.get(db=db, id=category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Only allow deleting user's own categories
    if db_category.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this category"
        )
    
    # Don't allow deleting system categories
    if db_category.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system categories"
        )
    
    # Check if category has transactions
    if category_service.has_transactions(db=db, category_id=category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with existing transactions"
        )
    
    category_service.delete(db=db, id=category_id)
    return {"message": "Category deleted successfully"}