# Standard library imports
from datetime import datetime
from typing import List, Dict, Annotated
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field

# Local imports
from .base import BaseResponseSchema
from ..models.goal import GoalStatus, GoalType, GoalPriority


class GoalBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )
    
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    target_amount_cents: Annotated[int, Field(gt=0, description="Target amount in cents")]
    goal_type: Annotated[GoalType, Field(default=GoalType.SAVINGS)]
    priority: Annotated[GoalPriority, Field(default=GoalPriority.MEDIUM)]
    status: Annotated[GoalStatus, Field(default=GoalStatus.ACTIVE)]
    start_date: datetime | None = None
    target_date: datetime | None = None
    last_contribution_date: datetime | None = None
    monthly_target_cents: int | None = Field(None, description="Monthly target in cents")
    milestone_percent: int | None = None

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date'] and v <= info.data['start_date']:
            raise ValueError('Target date must be after start date')
        return v

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    target_amount_cents: Annotated[int, Field(gt=0)] | None = None
    goal_type: GoalType | None = None
    priority: GoalPriority | None = None
    status: GoalStatus | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    monthly_target_cents: Annotated[int, Field(ge=0)] | None = None
    milestone_percentage: Annotated[int, Field(ge=1, le=100)] | None = None

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date'] and v <= info.data['start_date']:
            raise ValueError('Target date must be after start date')
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
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    user_id: UUID
    current_amount_cents: int
    completed_date: datetime | None = None
    last_contribution_date: datetime | None = None
    last_milestone: int | None = 0

    # Computed properties - made optional with defaults
    progress_percentage: int | None = 0
    remaining_amount_cents: int | None = 0
    is_completed: bool | None = False
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
    average_progress: int | float = 0
    this_month_contributions_cents: int
    # Detailed maps for UI charts
    goals_by_type: Dict[str, Dict[str, int]]
    goals_by_priority: Dict[str, Dict[str, int]]
    # Nested contribution stats block used by dashboard
    contribution_stats: Dict[str, List[dict] | int]

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

