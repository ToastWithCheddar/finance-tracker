# Standard library imports
import enum
from datetime import datetime
from typing import Optional, List, Dict, Annotated
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict, field_validator


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
    description: Optional[str] = None
    target_amount_cents: Annotated[int, Field(gt=0, description="Target amount in cents")]
    goal_type: Annotated[GoalType, Field(default=GoalType.SAVINGS)]
    priority: Annotated[GoalPriority, Field(default=GoalPriority.MEDIUM)]
    status: Annotated[GoalStatus, Field(default=GoalStatus.ACTIVE)]
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    auto_contribute: bool = False
    auto_contribution_amount_cents: Optional[int] = Field(None, description="Auto contribution amount in cents")
    auto_contribution_source: Optional[str] = None
    last_contribution_date: Optional[datetime] = None
    contribution_frequency: Annotated[ContributionFrequency, Field(default=ContributionFrequency.WEEKLY)]
    monthly_target_cents: Optional[int] = Field(None, description="Monthly target in cents")
    milestone_percent: Optional[int] = None

class GoalCreate(GoalBase):
    @field_validator('auto_contribution_amount_cents')
    @classmethod
    def validate_auto_contribution_amount(cls, v, info: dict):
        values = info.data
        if values.get('auto_contribute') and not v:
            raise ValueError("Auto contribution amount is required when auto-contribute is enabled")
        return v

class GoalUpdate(BaseModel):
    name: Optional[Annotated[str, Field(min_length=1, max_length=255)]] = None
    description: Optional[str] = None
    target_amount_cents: Optional[Annotated[int, Field(gt=0)]] = None
    goal_type: Optional[GoalType] = None
    priority: Optional[GoalPriority] = None
    status: Optional[GoalStatus] = None
    target_date: Optional[datetime] = None
    contribution_frequency: Optional[str] = None
    monthly_target_cents: Optional[Annotated[int, Field(ge=0)]] = None
    auto_contribute: Optional[bool] = None
    auto_contribution_amount_cents: Optional[Annotated[int, Field(ge=0)]] = None
    auto_contribution_source: Optional[str] = None
    milestone_percentage: Optional[Annotated[int, Field(ge=1.0, le=100.0)]] = None

# Contribution schemas
class GoalContributionBase(BaseModel):
    amount_cents: Annotated[int, Field(gt=0, description="Contribution amount in cents")]
    note: Optional[str] = None

class GoalContributionCreate(GoalContributionBase):
    pass

class GoalContribution(GoalContributionBase):
    id: UUID
    goal_id: UUID
    contribution_date: datetime = Field(default_factory=datetime.now)
    is_automatic: bool = False
    transaction_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Milestone schemas
class GoalMilestone(BaseModel):
    id: UUID
    goal_id: UUID 
    percentage: int
    amount_reached: int 
    reached_date: datetime
    celebrated: bool
    celebration_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Main Goal schema
class Goal(GoalBase):
    id: UUID
    user_id: UUID
    current_amount_cents: int
    status: GoalStatus
    start_date: datetime
    completed_date: Optional[datetime] = None
    last_contribution_date: Optional[datetime] = None
    last_milestone_reached: float
    created_at: datetime
    updated_at: datetime

    # Computed properties
    progress_percentage: int 
    remaining_amount_cents: int 
    is_completed: bool
    days_remaining: Optional[int] = None

    # Related data
    contributions: List[GoalContribution] = Field(default_factory=list)
    milestones: List[GoalMilestone] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

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


