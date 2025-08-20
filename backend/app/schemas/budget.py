from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum
from uuid import UUID

from .base import BaseResponseSchema
from .validation_types import PositiveAmount, DateRangeValidatorMixin


class BudgetPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class BudgetAlertType(str, Enum):
    WARNING = "warning"
    EXCEEDED = "exceeded"
    NEAR_END = "near_end"


class BudgetBase(BaseModel, DateRangeValidatorMixin):
    name: str = Field(..., min_length=1, max_length=100, description="Budget name")
    category_id: Optional[UUID] = Field(None, description="Category ID (None for overall budget)")
    amount_cents: PositiveAmount = Field(..., description="Budget amount in cents")
    period: BudgetPeriod = Field(..., description="Budget period")
    start_date: date = Field(..., description="Budget start date")
    end_date: Optional[date] = Field(None, description="Budget end date (None for recurring)")
    alert_threshold: float = Field(0.8, ge=0.1, le=1.0, description="Alert threshold (0.1-1.0)")
    is_active: bool = Field(True, description="Whether budget is active")


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category_id: Optional[UUID] = Field(None)
    amount_cents: Optional[int] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = Field(None)
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)
    alert_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    is_active: Optional[bool] = Field(None)

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date'] and v <= info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v


class BudgetUsage(BaseModel):
    budget_id: UUID
    spent_cents: int
    remaining_cents: int
    percentage_used: float
    is_over_budget: bool
    days_remaining: Optional[int] = Field(None, description="Days remaining in budget period")


class BudgetAlert(BaseModel):
    budget_id: UUID
    budget_name: str
    category_name: Optional[str]
    alert_type: BudgetAlertType
    message: str
    percentage_used: float
    amount_over: Optional[int] = Field(None, description="Amount over budget in cents")


class BudgetResponse(BudgetBase, BaseResponseSchema):
    user_id: UUID
    category_name: Optional[str] = Field(None, description="Category name if category_id is set")
    usage: Optional[BudgetUsage] = Field(None, description="Current usage statistics")
    has_custom_alerts: bool = Field(False, description="Whether this budget has custom alert settings")


class BudgetSummary(BaseModel):
    total_budgets: int
    active_budgets: int
    total_budgeted_cents: int
    total_spent_cents: int
    total_remaining_cents: int
    over_budget_count: int
    alert_count: int


class BudgetProgress(BaseModel):
    budget_id: UUID
    budget_name: str
    period_start: date
    period_end: date
    daily_spending: List[dict]  # [{date: str, amount_cents: int}]
    weekly_spending: List[dict]  # [{week: str, amount_cents: int}]
    category_breakdown: List[dict]  # [{category: str, amount_cents: int, percentage: float}]


class BudgetFilter(BaseModel):
    category_id: Optional[UUID] = Field(None, description="Filter by category")
    period: Optional[BudgetPeriod] = Field(None, description="Filter by period")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    start_date: Optional[date] = Field(None, description="Filter budgets starting after this date")
    end_date: Optional[date] = Field(None, description="Filter budgets ending before this date")
    over_budget: Optional[bool] = Field(None, description="Filter over-budget items")
    has_alerts: Optional[bool] = Field(None, description="Filter budgets with alerts")


class BudgetCalendarDay(BaseModel):
    date: date
    daily_spending_limit_cents: int
    actual_spending_cents: int
    percentage_used: float
    is_over_limit: bool
    transactions_count: int


class BudgetCalendarResponse(BaseModel):
    budget_id: UUID
    budget_name: str
    month: str  # YYYY-MM format
    period_start: date
    period_end: date
    daily_data: List[BudgetCalendarDay]
    summary: Dict[str, Any]  # Monthly summary stats


class BudgetListResponse(BaseModel):
    budgets: List[BudgetResponse]
    summary: BudgetSummary
    alerts: List[BudgetAlert]