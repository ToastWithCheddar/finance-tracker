from uuid import UUID
from datetime import date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class TimelineAnnotationBase(BaseModel):
    """Base schema for timeline annotations"""
    event_date: date = Field(..., description="Date of the timeline event")
    title: str = Field(..., min_length=1, max_length=200, description="Title of the annotation")
    description: Optional[str] = Field(None, description="Optional detailed description")
    icon: Optional[str] = Field(None, max_length=50, description="Emoji or icon name for the event")
    color: Optional[str] = Field(None, max_length=20, description="Hex color code for the event")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the annotation")


class TimelineAnnotationCreate(TimelineAnnotationBase):
    """Schema for creating a new timeline annotation"""
    pass


class TimelineAnnotationUpdate(BaseModel):
    """Schema for updating an existing timeline annotation"""
    event_date: Optional[date] = Field(None, description="Date of the timeline event")
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Title of the annotation")
    description: Optional[str] = Field(None, description="Optional detailed description")
    icon: Optional[str] = Field(None, max_length=50, description="Emoji or icon name for the event")
    color: Optional[str] = Field(None, max_length=20, description="Hex color code for the event")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the annotation")


class TimelineAnnotation(TimelineAnnotationBase):
    """Schema for timeline annotation responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Unique identifier for the annotation")
    user_id: UUID = Field(..., description="ID of the user who created the annotation")
    created_at: Optional[date] = Field(None, description="When the annotation was created")
    updated_at: Optional[date] = Field(None, description="When the annotation was last updated")


class TimelineEvent(BaseModel):
    """Unified schema for all timeline events (annotations, goals, transactions, etc.)"""
    id: str = Field(..., description="Unique identifier for the event")
    date: str = Field(..., description="ISO date string of the event")
    type: str = Field(..., description="Type of timeline event (annotation, goal, transaction, etc.)")
    title: str = Field(..., description="Display title of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    icon: str = Field(..., description="Icon or emoji representing the event")
    color: str = Field(..., description="Color for displaying the event")
    source: str = Field(..., description="Source system that generated the event")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")
    created_at: Optional[str] = Field(None, description="When the event was created")


class TimelineEventsList(BaseModel):
    """Response schema for timeline events listing"""
    events: List[TimelineEvent] = Field(..., description="List of timeline events")
    total_count: int = Field(..., description="Total number of events")
    start_date: str = Field(..., description="Start date of the timeline")
    end_date: str = Field(..., description="End date of the timeline")


class TimelineAnnotationsList(BaseModel):
    """Response schema for timeline annotations listing"""
    annotations: List[TimelineAnnotation] = Field(..., description="List of timeline annotations")
    total_count: int = Field(..., description="Total number of annotations")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")