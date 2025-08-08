"""
WebSocket message schemas for type-safe real-time communication
"""
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Message Types Enum
class MessageType(str, Enum):
    # Dashboard updates
    DASHBOARD_UPDATE = "dashboard_update"
    BALANCE_UPDATE = "balance_update"
    NET_WORTH_UPDATE = "net_worth_update"
    
    # Transaction events
    NEW_TRANSACTION = "new_transaction"
    TRANSACTION_UPDATED = "transaction_updated"
    TRANSACTION_DELETED = "transaction_deleted"
    BULK_TRANSACTIONS_IMPORTED = "bulk_transactions_imported"
    
    # Account events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_UPDATED = "account_updated"
    ACCOUNT_SYNCED = "account_synced"
    ACCOUNT_SYNC_ERROR = "account_sync_error"
    
    # Budget events
    BUDGET_ALERT = "budget_alert"
    BUDGET_THRESHOLD_REACHED = "budget_threshold_reached"
    BUDGET_EXCEEDED = "budget_exceeded"
    MONTHLY_BUDGET_RESET = "monthly_budget_reset"
    
    # Goal events
    GOAL_PROGRESS_UPDATE = "goal_progress_update"
    GOAL_ACHIEVED = "goal_achieved"
    GOAL_MILESTONE_REACHED = "goal_milestone_reached"
    
    # Insights and AI
    AI_INSIGHT_GENERATED = "ai_insight_generated"
    SPENDING_PATTERN_DETECTED = "spending_pattern_detected"
    CATEGORY_SUGGESTION = "category_suggestion"
    
    # System events
    NOTIFICATION = "notification"
    SYSTEM_ALERT = "system_alert"
    FULL_SYNC = "full_sync"
    PING = "ping"
    PONG = "pong"
    BATCH_UPDATE = "batch_update"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Base WebSocket Message
class WebSocketMessage(BaseModel):
    """Base WebSocket message structure"""
    id: str = Field(..., description="Unique message ID")
    type: MessageType = Field(..., description="Message type")
    timestamp: datetime = Field(..., description="Message timestamp")
    user_id: str = Field(..., description="Target user ID")

# Payload schemas for different message types

class DashboardUpdatePayload(BaseModel):
    total_balance: Optional[int] = Field(None, description="Total balance in cents")
    monthly_spending: Optional[int] = Field(None, description="Monthly spending in cents")
    monthly_income: Optional[int] = Field(None, description="Monthly income in cents")
    budget_utilization: Optional[float] = Field(None, description="Budget utilization percentage")
    active_goals: Optional[int] = Field(None, description="Number of active goals")
    recent_transactions: List[Dict[str, Any]] = Field(default_factory=list, description="Recent transactions")
    account_summary: Optional[Dict[str, Any]] = Field(None, description="Account summary")
    spending_by_category: List[Dict[str, Any]] = Field(default_factory=list, description="Spending by category")
    updated_at: datetime = Field(..., description="Update timestamp")

class BalanceUpdatePayload(BaseModel):
    account_id: str = Field(..., description="Account ID")
    account_name: str = Field(..., description="Account name")
    old_balance_cents: int = Field(..., description="Previous balance in cents")
    new_balance_cents: int = Field(..., description="New balance in cents")
    change_cents: int = Field(..., description="Balance change in cents")
    updated_at: datetime = Field(..., description="Update timestamp")

class TransactionPayload(BaseModel):
    id: str = Field(..., description="Transaction ID")
    amount_cents: int = Field(..., description="Transaction amount in cents")
    description: str = Field(..., description="Transaction description")
    merchant: Optional[str] = Field(None, description="Merchant name")
    category_id: Optional[str] = Field(None, description="Category ID")
    category_name: Optional[str] = Field(None, description="Category name")
    category_emoji: Optional[str] = Field(None, description="Category emoji")
    account_id: str = Field(..., description="Account ID")
    account_name: Optional[str] = Field(None, description="Account name")
    transaction_date: str = Field(..., description="Transaction date")
    created_at: Optional[str] = Field(None, description="Created timestamp")
    is_income: bool = Field(..., description="Whether transaction is income")

class BulkTransactionImportPayload(BaseModel):
    account_id: str = Field(..., description="Account ID")
    account_name: str = Field(..., description="Account name")
    transaction_count: int = Field(..., description="Number of imported transactions")
    imported_at: datetime = Field(..., description="Import timestamp")

class BudgetAlertPayload(BaseModel):
    budget_id: str = Field(..., description="Budget ID")
    budget_name: str = Field(..., description="Budget name")
    category_name: Optional[str] = Field(None, description="Category name")
    amount_cents: int = Field(..., description="Budget amount in cents")
    spent_cents: int = Field(..., description="Amount spent in cents")
    remaining_cents: int = Field(..., description="Remaining amount in cents")
    percentage_used: float = Field(..., description="Percentage of budget used")
    alert_type: str = Field(..., description="Alert type")
    priority: NotificationPriority = Field(..., description="Alert priority")
    message: str = Field(..., description="Alert message")
    period: str = Field(..., description="Budget period")
    threshold_reached: bool = Field(..., description="Whether threshold was reached")

class GoalProgressPayload(BaseModel):
    goal_id: str = Field(..., description="Goal ID")
    goal_name: str = Field(..., description="Goal name")
    target_amount_cents: int = Field(..., description="Target amount in cents")
    current_amount_cents: int = Field(..., description="Current amount in cents")
    remaining_cents: int = Field(..., description="Remaining amount in cents")
    progress_percentage: float = Field(..., description="Progress percentage")
    target_date: Optional[str] = Field(None, description="Target date")
    is_achieved: bool = Field(..., description="Whether goal is achieved")
    milestone_reached: bool = Field(..., description="Whether milestone was reached")

class GoalAchievedPayload(BaseModel):
    goal_id: str = Field(..., description="Goal ID")
    goal_name: str = Field(..., description="Goal name")
    target_amount_cents: int = Field(..., description="Target amount in cents")
    achieved_amount_cents: int = Field(..., description="Achieved amount in cents")
    achievement_date: datetime = Field(..., description="Achievement timestamp")
    celebration_message: str = Field(..., description="Celebration message")
    priority: NotificationPriority = Field(..., description="Message priority")

class AccountSyncPayload(BaseModel):
    account_id: str = Field(..., description="Account ID")
    account_name: Optional[str] = Field(None, description="Account name")
    transactions_added: int = Field(0, description="Number of transactions added")
    balance_updated: bool = Field(False, description="Whether balance was updated")
    new_balance_cents: Optional[int] = Field(None, description="New balance in cents")
    sync_duration_ms: Optional[int] = Field(None, description="Sync duration in milliseconds")
    synced_at: datetime = Field(..., description="Sync timestamp")
    success: bool = Field(True, description="Whether sync was successful")

class AccountSyncErrorPayload(BaseModel):
    account_id: str = Field(..., description="Account ID")
    account_name: Optional[str] = Field(None, description="Account name")
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    retry_suggested: bool = Field(True, description="Whether retry is suggested")
    failed_at: datetime = Field(..., description="Failure timestamp")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Error priority")

class NotificationPayload(BaseModel):
    id: str = Field(..., description="Notification ID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: Literal["success", "error", "warning", "info"] = Field("info", description="Notification type")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Notification priority")
    action_url: Optional[str] = Field(None, description="Action URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    read: bool = Field(False, description="Whether notification is read")

class SystemAlertPayload(BaseModel):
    alert_type: str = Field(..., description="Alert type")
    message: str = Field(..., description="Alert message")
    priority: NotificationPriority = Field(NotificationPriority.HIGH, description="Alert priority")
    system_wide: bool = Field(True, description="Whether alert is system-wide")
    created_at: datetime = Field(..., description="Creation timestamp")

class AIInsightPayload(BaseModel):
    insight_id: str = Field(..., description="Insight ID")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    insight_type: str = Field(..., description="Insight type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Insight data")
    confidence_score: Optional[float] = Field(None, description="Confidence score")
    actionable: bool = Field(False, description="Whether insight is actionable")
    action_items: List[str] = Field(default_factory=list, description="Action items")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Insight priority")
    generated_at: datetime = Field(..., description="Generation timestamp")

class PingPayload(BaseModel):
    server_time: datetime = Field(..., description="Server timestamp")
    connection_status: Literal["active", "idle"] = Field("active", description="Connection status")

class BatchUpdatePayload(BaseModel):
    events: List[Dict[str, Any]] = Field(..., description="Batch events")
    count: int = Field(..., description="Number of events")
    batch_id: str = Field(..., description="Batch ID")

# Union type for all possible payloads
PayloadType = Union[
    DashboardUpdatePayload,
    BalanceUpdatePayload,
    TransactionPayload,
    BulkTransactionImportPayload,
    BudgetAlertPayload,
    GoalProgressPayload,
    GoalAchievedPayload,
    AccountSyncPayload,
    AccountSyncErrorPayload,
    NotificationPayload,
    SystemAlertPayload,
    AIInsightPayload,
    PingPayload,
    BatchUpdatePayload,
]

# Typed WebSocket Messages
class TypedWebSocketMessage(WebSocketMessage):
    """Typed WebSocket message with payload"""
    payload: PayloadType = Field(..., description="Message payload")

# Message factory functions for type safety
def create_dashboard_update_message(user_id: str, payload: DashboardUpdatePayload) -> TypedWebSocketMessage:
    return TypedWebSocketMessage(
        id=f"dashboard_{datetime.utcnow().timestamp()}",
        type=MessageType.DASHBOARD_UPDATE,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        payload=payload
    )

def create_transaction_message(user_id: str, payload: TransactionPayload) -> TypedWebSocketMessage:
    return TypedWebSocketMessage(
        id=f"transaction_{datetime.utcnow().timestamp()}",
        type=MessageType.NEW_TRANSACTION,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        payload=payload
    )

def create_budget_alert_message(user_id: str, payload: BudgetAlertPayload) -> TypedWebSocketMessage:
    return TypedWebSocketMessage(
        id=f"budget_alert_{datetime.utcnow().timestamp()}",
        type=MessageType.BUDGET_ALERT,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        payload=payload
    )

def create_goal_progress_message(user_id: str, payload: GoalProgressPayload) -> TypedWebSocketMessage:
    return TypedWebSocketMessage(
        id=f"goal_progress_{datetime.utcnow().timestamp()}",
        type=MessageType.GOAL_PROGRESS_UPDATE,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        payload=payload
    )

def create_notification_message(user_id: str, payload: NotificationPayload) -> TypedWebSocketMessage:
    return TypedWebSocketMessage(
        id=f"notification_{datetime.utcnow().timestamp()}",
        type=MessageType.NOTIFICATION,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        payload=payload
    )

# Validation helper
def validate_websocket_message(data: Dict[str, Any]) -> TypedWebSocketMessage:
    """Validate and parse WebSocket message data"""
    return TypedWebSocketMessage.model_validate(data)