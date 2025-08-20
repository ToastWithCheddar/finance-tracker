from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from .base import BaseResponseSchema
from .validation_types import (
    NonNegativeAmount, DateRangeValidatorMixin, UUIDList, 
    TagList, TransactionType
)


class DateRangeFilter(BaseModel, DateRangeValidatorMixin):
    """Schema for date range filters"""
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")


class AmountRangeFilter(BaseModel):
    """Schema for amount range filters"""
    min_cents: NonNegativeAmount = Field(None, description="Minimum amount in cents")
    max_cents: NonNegativeAmount = Field(None, description="Maximum amount in cents")
    
    @validator('max_cents')
    def validate_max_greater_than_min(cls, v, values):
        if v is not None and 'min_cents' in values and values['min_cents'] is not None:
            if v <= values['min_cents']:
                raise ValueError('max_cents must be greater than min_cents')
        return v


class FilterConfiguration(BaseModel):
    """Strongly typed schema for filter configuration"""
    date_range: Optional[DateRangeFilter] = Field(None, description="Date range filter")
    amount_range: Optional[AmountRangeFilter] = Field(None, description="Amount range filter")
    categories: UUIDList = Field(None, description="Category IDs to filter by")
    accounts: UUIDList = Field(None, description="Account IDs to filter by")
    search_text: Optional[str] = Field(None, max_length=200, description="Text search in description/merchant")
    transaction_types: Optional[List[TransactionType]] = Field(None, description="Transaction types (debit/credit)")
    tags: TagList = Field(None, description="Tags to filter by")


class SavedFilterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the saved filter")
    filters: FilterConfiguration = Field(..., description="Filter configuration")


class SavedFilterCreate(SavedFilterBase):
    pass


class SavedFilterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the saved filter")
    filters: Optional[FilterConfiguration] = Field(None, description="Filter configuration")
    
    @validator('filters')
    def validate_filters_not_empty(cls, v):
        """Ensure at least one filter is specified when updating"""
        if v is not None:
            if not any([v.date_range, v.amount_range, v.categories, v.accounts, 
                       v.search_text, v.transaction_types, v.tags]):
                raise ValueError('At least one filter must be specified')
        return v


class SavedFilterResponse(SavedFilterBase, BaseResponseSchema):
    user_id: UUID