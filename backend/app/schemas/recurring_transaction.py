# Standard library imports
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from decimal import Decimal

# Third-party imports
from pydantic import BaseModel, Field, validator, root_validator

# Local imports
from app.models.recurring_transaction import FrequencyType

# Base schemas
class RecurringTransactionRuleBase(BaseModel):
    """Base schema for recurring transaction rules."""
    
    name: str = Field(..., min_length=1, max_length=200, description="User-friendly name for the rule")
    description: str = Field(..., min_length=1, max_length=500, description="Description or merchant name")
    amount_cents: int = Field(..., ge=1, description="Expected amount in cents")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$", description="Currency code")
    
    frequency: FrequencyType = Field(..., description="Frequency of recurrence")
    interval: int = Field(default=1, ge=1, le=12, description="Interval multiplier (e.g., every 2 months)")
    
    start_date: date = Field(..., description="When the rule becomes active")
    end_date: Optional[date] = Field(None, description="Optional end date")
    
    tolerance_cents: int = Field(default=500, ge=0, description="Amount tolerance in cents")
    auto_categorize: bool = Field(default=True, description="Auto-apply category to matching transactions")
    generate_notifications: bool = Field(default=True, description="Send reminder notifications")
    
    notification_settings: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")
    custom_rule: Optional[Dict[str, Any]] = Field(None, description="Custom frequency rules")
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('amount_cents')
    def validate_amount_cents(cls, v):
        if v <= 0:
            raise ValueError('amount_cents must be positive')
        return v

class RecurringTransactionRuleCreate(RecurringTransactionRuleBase):
    """Schema for creating recurring transaction rules."""
    
    account_id: UUID = Field(..., description="Account ID for the rule")
    category_id: Optional[UUID] = Field(None, description="Category ID for auto-categorization")

class RecurringTransactionRuleUpdate(BaseModel):
    """Schema for updating recurring transaction rules."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    amount_cents: Optional[int] = Field(None, ge=1)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    
    frequency: Optional[FrequencyType] = None
    interval: Optional[int] = Field(None, ge=1, le=12)
    
    end_date: Optional[date] = None
    next_due_date: Optional[date] = None
    
    tolerance_cents: Optional[int] = Field(None, ge=0)
    auto_categorize: Optional[bool] = None
    generate_notifications: Optional[bool] = None
    is_active: Optional[bool] = None
    
    category_id: Optional[UUID] = None
    notification_settings: Optional[Dict[str, Any]] = None
    custom_rule: Optional[Dict[str, Any]] = None
    
    @validator('amount_cents')
    def validate_amount_cents(cls, v):
        if v is not None and v <= 0:
            raise ValueError('amount_cents must be positive')
        return v

class RecurringTransactionRuleResponse(RecurringTransactionRuleBase):
    """Schema for returning recurring transaction rules."""
    
    id: UUID
    user_id: UUID
    account_id: UUID
    category_id: Optional[UUID]
    
    next_due_date: date
    last_generated_date: Optional[date]
    last_matched_at: Optional[datetime]
    
    is_active: bool
    is_confirmed: bool
    confidence_score: Optional[float]
    detection_method: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    amount_dollars: Optional[Decimal] = None
    days_until_next: Optional[int] = None
    
    class Config:
        from_attributes = True
        
    @root_validator(skip_on_failure=True)
    def compute_derived_fields(cls, values):
        # Calculate amount in dollars
        if 'amount_cents' in values and values['amount_cents']:
            values['amount_dollars'] = Decimal(values['amount_cents']) / 100
        
        # Calculate days until next occurrence
        if 'next_due_date' in values and values['next_due_date']:
            today = date.today()
            delta = values['next_due_date'] - today
            values['days_until_next'] = delta.days
            
        return values

# Suggestion schemas
class RecurringSuggestion(BaseModel):
    """Schema for recurring transaction suggestions."""
    
    id: str = Field(..., description="Unique identifier for the suggestion")
    merchant: str = Field(..., description="Merchant or description")
    normalized_merchant: str = Field(..., description="Normalized merchant name")
    
    amount_cents: int = Field(..., description="Average amount in cents")
    amount_dollars: float = Field(..., description="Average amount in dollars")
    currency: str = Field(default="USD", description="Currency code")
    
    frequency: str = Field(..., description="Detected frequency")
    interval: int = Field(default=1, description="Interval multiplier")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    
    account_id: UUID = Field(..., description="Account ID")
    category_id: Optional[UUID] = Field(None, description="Most common category")
    
    transaction_count: int = Field(..., description="Number of transactions in pattern")
    sample_dates: List[str] = Field(..., description="Sample transaction dates")
    next_expected_date: str = Field(..., description="Next expected transaction date")
    
    amount_variation: Dict[str, Any] = Field(..., description="Amount variation statistics")
    detection_method: str = Field(..., description="Detection method used")

class SuggestionApproval(BaseModel):
    """Schema for approving a suggestion."""
    
    suggestion_id: str = Field(..., description="ID of the suggestion to approve")
    
    # Optional overrides
    name: Optional[str] = Field(None, max_length=200, description="Custom name override")
    category_id: Optional[UUID] = Field(None, description="Category override")
    amount_cents: Optional[int] = Field(None, ge=1, description="Amount override")
    tolerance_cents: Optional[int] = Field(None, ge=0, description="Tolerance override")
    auto_categorize: Optional[bool] = Field(None, description="Auto-categorize override")
    generate_notifications: Optional[bool] = Field(None, description="Notifications override")

# List and pagination schemas
class RecurringRuleFilter(BaseModel):
    """Schema for filtering recurring transaction rules."""
    
    is_active: Optional[bool] = None
    is_confirmed: Optional[bool] = None
    frequency: Optional[FrequencyType] = None
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    
    # Date filters
    next_due_from: Optional[date] = None
    next_due_to: Optional[date] = None
    
    # Amount filters  
    min_amount_cents: Optional[int] = Field(None, ge=0)
    max_amount_cents: Optional[int] = Field(None, ge=0)
    
    # Text search
    search: Optional[str] = Field(None, max_length=200, description="Search in name/description")
    
    @validator('max_amount_cents')
    def validate_amount_range(cls, v, values):
        if v and 'min_amount_cents' in values and values['min_amount_cents'] and v < values['min_amount_cents']:
            raise ValueError('max_amount_cents must be greater than min_amount_cents')
        return v

class PaginatedRecurringRulesResponse(BaseModel):
    """Paginated response for recurring rules."""
    
    items: List[RecurringTransactionRuleResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    # Summary statistics
    active_rules: int
    upcoming_in_week: int
    total_monthly_amount_cents: int
    
class RecurringRuleStats(BaseModel):
    """Statistics about recurring rules."""
    
    total_rules: int
    active_rules: int
    inactive_rules: int
    confirmed_rules: int
    suggested_rules: int
    
    # By frequency
    weekly_count: int
    monthly_count: int
    quarterly_count: int
    annual_count: int
    
    # Financial stats
    total_monthly_amount_cents: int
    average_amount_cents: int
    
    # Upcoming
    due_this_week: int
    due_next_week: int
    overdue: int

# Error schemas
class RecurringTransactionError(BaseModel):
    """Error response for recurring transaction operations."""
    
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None