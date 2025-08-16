from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from .base import BaseResponseSchema


class InsightType(str, Enum):
    SPENDING_SPIKE = "spending_spike"
    SAVINGS_OPPORTUNITY = "savings_opportunity"
    BUDGET_ALERT = "budget_alert"
    SPENDING_PATTERN = "spending_pattern"
    GOAL_PROGRESS = "goal_progress"
    CASHFLOW_ANALYSIS = "cashflow_analysis"
    RECURRING_EXPENSE = "recurring_expense"
    UNUSUAL_TRANSACTION = "unusual_transaction"


class InsightPriority(int, Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class InsightBase(BaseModel):
    type: InsightType = Field(..., description="Type of insight")
    title: str = Field(..., min_length=1, max_length=200, description="Insight title")
    description: str = Field(..., min_length=1, description="Detailed insight description")
    priority: InsightPriority = Field(InsightPriority.MEDIUM, description="Insight priority")
    is_read: bool = Field(False, description="Whether insight has been read")
    extra_payload: Optional[Dict[str, Any]] = Field(None, description="Additional insight data")


class InsightCreate(InsightBase):
    user_id: UUID = Field(..., description="User ID")
    transaction_id: Optional[UUID] = Field(None, description="Related transaction ID")


class InsightUpdate(BaseModel):
    is_read: Optional[bool] = Field(None, description="Mark insight as read/unread")


class InsightResponse(InsightBase, BaseResponseSchema):
    user_id: UUID
    transaction_id: Optional[UUID] = Field(None, description="Related transaction ID")
    

class InsightListResponse(BaseModel):
    insights: List[InsightResponse]
    total_count: int
    unread_count: int


class InsightFilter(BaseModel):
    type: Optional[InsightType] = Field(None, description="Filter by insight type")
    priority: Optional[InsightPriority] = Field(None, description="Filter by priority")
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    limit: int = Field(30, ge=1, le=100, description="Number of insights to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")