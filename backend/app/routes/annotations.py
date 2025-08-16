from uuid import UUID
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user, get_db_with_user_context
from ..models import User, TimelineAnnotation
from ..schemas.timeline_annotation import (
    TimelineAnnotationCreate,
    TimelineAnnotationUpdate,
    TimelineAnnotation as TimelineAnnotationSchema,
    TimelineAnnotationsList
)

router = APIRouter(prefix="/api/annotations", tags=["Timeline Annotations"])


@router.post("/", response_model=TimelineAnnotationSchema, status_code=201)
async def create_annotation(
    annotation_data: TimelineAnnotationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user_context)
):
    """Create a new timeline annotation for the current user."""
    
    # Create the new annotation
    new_annotation = TimelineAnnotation(
        user_id=current_user.id,
        date=annotation_data.date,
        title=annotation_data.title,
        description=annotation_data.description,
        icon=annotation_data.icon,
        color=annotation_data.color,
        extra_data=annotation_data.extra_data
    )
    
    db.add(new_annotation)
    await db.commit()
    await db.refresh(new_annotation)
    
    return new_annotation


@router.get("/", response_model=TimelineAnnotationsList)
async def get_annotations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Number of items per page"),
    start_date: Optional[date] = Query(None, description="Filter annotations from this date"),
    end_date: Optional[date] = Query(None, description="Filter annotations to this date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user_context)
):
    """Get paginated list of timeline annotations for the current user."""
    
    # Build query
    query = select(TimelineAnnotation).where(TimelineAnnotation.user_id == current_user.id)
    
    # Apply date filters
    if start_date:
        query = query.where(TimelineAnnotation.date >= start_date)
    if end_date:
        query = query.where(TimelineAnnotation.date <= end_date)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(TimelineAnnotation.date), desc(TimelineAnnotation.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    annotations = result.scalars().all()
    
    return TimelineAnnotationsList(
        annotations=annotations,
        total_count=total_count,
        page=page,
        limit=limit
    )


@router.get("/{annotation_id}", response_model=TimelineAnnotationSchema)
async def get_annotation(
    annotation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user_context)
):
    """Get a specific timeline annotation by ID."""
    
    query = select(TimelineAnnotation).where(
        TimelineAnnotation.id == annotation_id,
        TimelineAnnotation.user_id == current_user.id
    )
    
    result = await db.execute(query)
    annotation = result.scalar_one_or_none()
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Timeline annotation not found")
    
    return annotation


@router.put("/{annotation_id}", response_model=TimelineAnnotationSchema)
async def update_annotation(
    annotation_id: UUID,
    annotation_data: TimelineAnnotationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user_context)
):
    """Update a timeline annotation."""
    
    query = select(TimelineAnnotation).where(
        TimelineAnnotation.id == annotation_id,
        TimelineAnnotation.user_id == current_user.id
    )
    
    result = await db.execute(query)
    annotation = result.scalar_one_or_none()
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Timeline annotation not found")
    
    # Update fields if provided
    update_data = annotation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(annotation, field, value)
    
    await db.commit()
    await db.refresh(annotation)
    
    return annotation


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user_context)
):
    """Delete a timeline annotation."""
    
    query = select(TimelineAnnotation).where(
        TimelineAnnotation.id == annotation_id,
        TimelineAnnotation.user_id == current_user.id
    )
    
    result = await db.execute(query)
    annotation = result.scalar_one_or_none()
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Timeline annotation not found")
    
    await db.delete(annotation)
    await db.commit()
    
    return None