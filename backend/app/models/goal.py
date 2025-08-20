# Standard library imports
import enum
from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID

# Third-party imports
from sqlalchemy import String, Integer, BigInteger, Date, Text, ForeignKey, Boolean, Enum, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, mapped_column, Mapped

# Local imports
from .base import BaseModel

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


class Goal(BaseModel):
    __tablename__ = "goals"
    
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    target_amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_amount_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType), nullable=False)
    priority: Mapped[GoalPriority] = mapped_column(Enum(GoalPriority), default=GoalPriority.MEDIUM)
    status: Mapped[GoalStatus] = mapped_column(Enum(GoalStatus), default=GoalStatus.ACTIVE)
    
    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Auto-contribution settings
    auto_contribute: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_contribution_amount_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    auto_contribution_source: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., "checking_account"

    # Progress tracking
    last_contribution_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contribution_frequency: Mapped[ContributionFrequency] = mapped_column(Enum(ContributionFrequency), default=ContributionFrequency.WEEKLY)
    monthly_target_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    celebration_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Milestone settings 
    milestone_percent: Mapped[int] = mapped_column(Integer, default=25, nullable=True) # Round up
    last_milestone: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) 

    # Relationships 
    user = relationship("User", back_populates="goals") # One user can have many goals
    contributions = relationship('GoalContribution', back_populates='goal', cascade="all, delete-orphan") # One goal can have many contributions
    milestones = relationship('GoalMilestone', back_populates='goal', cascade="all, delete-orphan") # One goal can have many milestones
    
    @property
    def progress_percentage(self) -> int:
        if self.target_amount_cents <= 0:
            return 0
        return min(int((self.current_amount_cents / self.target_amount_cents) * 100), 100)

    @property
    def remaining(self) -> int:
        return max(0, int(self.target_amount_cents - self.current_amount_cents))

    @property
    def is_achieved(self) -> bool:
        return self.current_amount_cents >= self.target_amount_cents

    @property
    def days_remaining(self) -> int:
        if not self.target_date:
            return 0
        return max((self.target_date - datetime.now(timezone.utc).date()).days, 0)
    
    def __repr__(self):
        return f"<Goal(id={self.id}, name='{self.name}', target_cents={self.target_amount_cents}, status={self.status.value})>"
    
    __table_args__ = (
        Index('idx_goal_user_status', 'user_id', 'status'),
        Index('idx_goal_user_type', 'user_id', 'goal_type'),
        Index('idx_goal_target_date', 'target_date'),
        Index('idx_goal_priority_status', 'priority', 'status'),
    )

class GoalContribution(BaseModel):
    __tablename__ = "goal_contributions"

    goal_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)

    # Relationships
    goal = relationship("Goal", back_populates="contributions")
    transaction = relationship("Transaction", back_populates="goal_contributions")
    
    def __repr__(self):
        return f"<GoalContribution(id={self.id}, goal_id={self.goal_id}, amount_cents={self.amount_cents}, date={self.contribution_date})>"
    
    __table_args__ = (
        Index('idx_contribution_goal_date', 'goal_id', 'contribution_date'),
        Index('idx_contribution_transaction', 'transaction_id'),
    )

class GoalMilestone(BaseModel):
    __tablename__ = "goal_milestones"

    goal_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_reached_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reached_date: Mapped[date] = mapped_column(Date, default=lambda: datetime.now(timezone.utc).date())

    # Relationships
    goal = relationship("Goal", back_populates="milestones") # One goal can have many milestones
    
    def __repr__(self):
        return f"<GoalMilestone(id={self.id}, goal_id={self.goal_id}, percentage={self.percentage}%, date={self.reached_date})>"
    
    __table_args__ = (
        Index('idx_milestone_goal_percentage', 'goal_id', 'percentage'),
        Index('idx_milestone_reached_date', 'reached_date'),
    )