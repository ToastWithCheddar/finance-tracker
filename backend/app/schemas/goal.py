# Standard library imports
import enum
from datetime import datetime
from typing import List, Dict, Annotated
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Local imports
from .base import BaseResponseSchema


class GoalStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class GoalType(enum.Enum):
    SAVINGS = "savings"
    DEBT_PAYOFF = "debt_payoff"
    EMERGENCY_FUND = "emergency_fund"
    INVESTMENT = "investment"
    PURCHASE = "purchase"
    OTHER = "other"

class GoalPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ContributionFrequency(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class GoalBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    target_amount_cents: Annotated[int, Field(gt=0, description="Target amount in cents")]
    goal_type: Annotated[GoalType, Field(default=GoalType.SAVINGS)]
    priority: Annotated[GoalPriority, Field(default=GoalPriority.MEDIUM)]
    status: Annotated[GoalStatus, Field(default=GoalStatus.ACTIVE)]
    start_date: datetime | None = None
    target_date: datetime | None = None
    auto_contribute: bool = False
    auto_contribution_amount_cents: int | None = Field(None, description="Auto contribution amount in cents")
    auto_contribution_source: str | None = None
    last_contribution_date: datetime | None = None
    contribution_frequency: Annotated[ContributionFrequency, Field(default=ContributionFrequency.WEEKLY)]
    monthly_target_cents: int | None = Field(None, description="Monthly target in cents")
    milestone_percent: int | None = None

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date'] and v <= info.data['start_date']:
            raise ValueError('Target date must be after start date')
        return v

class GoalCreate(GoalBase):
    @field_validator('auto_contribution_amount_cents')
    @classmethod
    def validate_auto_contribution_amount(cls, v, info: dict):
        values = info.data
        if values.get('auto_contribute') and not v:
            raise ValueError("Auto contribution amount is required when auto-contribute is enabled")
        return v

class GoalUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    target_amount_cents: Annotated[int, Field(gt=0)] | None = None
    goal_type: GoalType | None = None
    priority: GoalPriority | None = None
    status: GoalStatus | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    contribution_frequency: ContributionFrequency | None = None
    monthly_target_cents: Annotated[int, Field(ge=0)] | None = None
    auto_contribute: bool | None = None
    auto_contribution_amount_cents: Annotated[int, Field(gt=0)] | None = None
    auto_contribution_source: str | None = None
    milestone_percentage: Annotated[int, Field(ge=1, le=100)] | None = None

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date'] and v <= info.data['start_date']:
            raise ValueError('Target date must be after start date')
        return v

    @field_validator('auto_contribution_amount_cents')
    @classmethod
    def validate_auto_contribution_amount(cls, v, info):
        values = info.data
        if values.get('auto_contribute') and not v:
            raise ValueError("Auto contribution amount is required when auto-contribute is enabled")
        if not values.get('auto_contribute') and v:
            raise ValueError("Auto contribution amount should not be set when auto-contribute is disabled")
        return v

    @field_validator('monthly_target_cents')
    @classmethod
    def validate_monthly_target(cls, v, info):
        values = info.data
        target_amount = values.get('target_amount_cents')
        if v and target_amount and v > target_amount:
            raise ValueError("Monthly target cannot exceed total goal target amount")
        return v

# Contribution schemas
class GoalContributionBase(BaseModel):
    amount_cents: Annotated[int, Field(gt=0, description="Contribution amount in cents")]
    note: str | None = None

class GoalContributionCreate(GoalContributionBase):
    pass

class GoalContribution(GoalContributionBase, BaseResponseSchema):
    goal_id: UUID
    contribution_date: datetime = Field(default_factory=datetime.now)
    is_automatic: bool = False
    transaction_id: UUID | None = None

# Milestone schemas
class GoalMilestone(BaseResponseSchema):
    goal_id: UUID 
    percentage: int
    amount_reached: int 
    reached_date: datetime
    celebrated: bool
    celebration_message: str | None = None

# Main Goal schema
class Goal(GoalBase, BaseResponseSchema):
    user_id: UUID
    current_amount_cents: int
    status: GoalStatus
    start_date: datetime
    completed_date: datetime | None = None
    last_contribution_date: datetime | None = None
    last_milestone_reached: float

    # Computed properties
    progress_percentage: int 
    remaining_amount_cents: int 
    is_completed: bool
    days_remaining: int | None = None

    # Related data
    contributions: List[GoalContribution] = Field(default_factory=list)
    milestones: List[GoalMilestone] = Field(default_factory=list)

# Response schemas
class GoalsResponse(BaseModel):
    goals: List[Goal]
    total: int
    active_goals: int
    completed_goals: int
    total_target_amount_cents: int 
    total_current_amount_cents: int 

class GoalStats(BaseModel):
    total_goals: int
    active_goals: int
    completed_goals: int
    paused_goals: int
    total_saved_cents: int 
    total_target_cents: int 
    this_month_contributions_cents: int 
    goals_by_type: Dict[str, int]
    goals_by_priority: Dict[str, int]

class ContributionStats(BaseModel):
    total_contributions_cents: int 
    this_month_cents: int 
    last_month_cents: int
    average_monthly_cents: int 
    contribution_trend: List[dict]  # Monthly data for charts

class MilestoneAlert(BaseModel):
    goal_id: UUID
    goal_name: str
    milestone_percentage: int 
    amount_reached_cents: int 
    reached_date: datetime


