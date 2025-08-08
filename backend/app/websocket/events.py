# backend/app/websocket/events.py
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from enum import Enum

from .manager import websocket_manager as manager
from .schemas import (
    MessageType, NotificationPriority,
    create_dashboard_update_message, create_transaction_message,
    create_budget_alert_message, create_goal_progress_message,
    create_notification_message, DashboardUpdatePayload,
    TransactionPayload, BudgetAlertPayload, GoalProgressPayload,
    GoalAchievedPayload, AccountSyncPayload, AccountSyncErrorPayload,
    NotificationPayload, SystemAlertPayload, AIInsightPayload,
    PingPayload, BulkTransactionImportPayload, BalanceUpdatePayload
)

logger = logging.getLogger(__name__)


class EventType(Enum):
    """WebSocket event types"""
    DASHBOARD_UPDATE = "dashboard_update"
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_UPDATED = "transaction_updated"
    TRANSACTION_DELETED = "transaction_deleted"
    ACCOUNT_CONNECTED = "account_connected"
    ACCOUNT_BALANCE_UPDATED = "account_balance_updated"
    BUDGET_ALERT = "budget_alert"
    GOAL_PROGRESS = "goal_progress"
    NOTIFICATION = "notification"
    SYNC_STATUS = "sync_status"


class WebSocketEvent:
    """WebSocket event wrapper"""
    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp
        }

class WebSocketEvents:
    """Enhanced WebSocket event emitters for real-time updates"""

    # ========== DASHBOARD EVENTS ==========
    
    @staticmethod
    async def emit_dashboard_update(user_id: str, dashboard_data: Dict[str, Any]):
        """Emit comprehensive dashboard update"""
        payload = DashboardUpdatePayload(
            total_balance=dashboard_data.get("total_balance"),
            monthly_spending=dashboard_data.get("monthly_spending"),
            monthly_income=dashboard_data.get("monthly_income"),
            budget_utilization=dashboard_data.get("budget_utilization"),
            active_goals=dashboard_data.get("active_goals"),
            recent_transactions=dashboard_data.get("recent_transactions", [])[:5],
            account_summary=dashboard_data.get("account_summary"),
            spending_by_category=dashboard_data.get("spending_by_category", []),
            updated_at=datetime.utcnow()
        )
        message = create_dashboard_update_message(user_id, payload)
        await manager.send_to_user(user_id, message.model_dump())

    @staticmethod
    async def emit_balance_update(user_id: str, account_id: str, old_balance: int, new_balance: int, account_name: str):
        """Emit account balance change"""
        payload = BalanceUpdatePayload(
            account_id=account_id,
            account_name=account_name,
            old_balance_cents=old_balance,
            new_balance_cents=new_balance,
            change_cents=new_balance - old_balance,
            updated_at=datetime.utcnow()
        )
        message = {
            "id": f"balance_{datetime.utcnow().timestamp()}",
            "type": MessageType.BALANCE_UPDATE,
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "payload": payload.model_dump()
        }
        await manager.send_to_user(user_id, message)

    # ========== TRANSACTION EVENTS ==========
    
    @staticmethod
    async def emit_new_transaction(user_id: str, transaction_data: Dict[str, Any]):
        """Emit new transaction created"""
        message = {
            "type": MessageType.NEW_TRANSACTION,
            "payload": {
                "id": transaction_data.get("id"),
                "amount_cents": transaction_data.get("amount_cents"),
                "description": transaction_data.get("description"),
                "merchant": transaction_data.get("merchant"),
                "category_id": transaction_data.get("category_id"),
                "category_name": transaction_data.get("category", {}).get("name"),
                "category_emoji": transaction_data.get("category", {}).get("emoji"),
                "account_id": transaction_data.get("account_id"),
                "account_name": transaction_data.get("account", {}).get("name"),
                "transaction_date": transaction_data.get("transaction_date"),
                "created_at": transaction_data.get("created_at"),
                "is_income": transaction_data.get("amount_cents", 0) > 0
            }
        }
        await manager.send_to_user(user_id, message)

    @staticmethod
    async def emit_bulk_transactions_imported(user_id: str, account_id: str, count: int, account_name: str):
        """Emit bulk transaction import completion"""
        message = {
            "type": MessageType.BULK_TRANSACTIONS_IMPORTED,
            "payload": {
                "account_id": account_id,
                "account_name": account_name,
                "transaction_count": count,
                "imported_at": datetime.utcnow().isoformat()
            }
        }
        await manager.send_to_user(user_id, message)

    # ========== BUDGET EVENTS ==========
    
    @staticmethod
    async def emit_budget_alert(user_id: str, budget_data: Dict[str, Any], alert_type: str = "threshold"):
        """Emit budget alert with different severity levels"""
        spent_percentage = (budget_data.get("spent_cents", 0) / budget_data.get("amount_cents", 1)) * 100
        
        # Determine priority based on spending percentage
        if spent_percentage >= 100:
            priority = NotificationPriority.CRITICAL
            alert_message = f"Budget exceeded! You've spent {spent_percentage:.1f}% of your {budget_data.get('name')} budget."
        elif spent_percentage >= 90:
            priority = NotificationPriority.HIGH
            alert_message = f"Budget warning: {spent_percentage:.1f}% of your {budget_data.get('name')} budget used."
        elif spent_percentage >= 75:
            priority = NotificationPriority.MEDIUM
            alert_message = f"Budget update: {spent_percentage:.1f}% of your {budget_data.get('name')} budget used."
        else:
            priority = NotificationPriority.LOW
            alert_message = f"Budget check: {spent_percentage:.1f}% of your {budget_data.get('name')} budget used."

        message = {
            "type": MessageType.BUDGET_ALERT,
            "payload": {
                "budget_id": budget_data.get("id"),
                "budget_name": budget_data.get("name"),
                "category_name": budget_data.get("category", {}).get("name"),
                "amount_cents": budget_data.get("amount_cents"),
                "spent_cents": budget_data.get("spent_cents"),
                "remaining_cents": budget_data.get("remaining_cents"),
                "percentage_used": spent_percentage,
                "alert_type": alert_type,
                "priority": priority,
                "message": alert_message,
                "period": budget_data.get("period"),
                "threshold_reached": spent_percentage >= budget_data.get("alert_threshold", 80)
            }
        }
        await manager.send_to_user(user_id, message)

    # ========== GOAL EVENTS ==========
    
    @staticmethod
    async def emit_goal_progress_update(user_id: str, goal_data: Dict[str, Any]):
        """Emit goal progress update"""
        progress_percentage = (goal_data.get("current_amount_cents", 0) / goal_data.get("target_amount_cents", 1)) * 100
        
        message = {
            "type": MessageType.GOAL_PROGRESS_UPDATE,
            "payload": {
                "goal_id": goal_data.get("id"),
                "goal_name": goal_data.get("name"),
                "target_amount_cents": goal_data.get("target_amount_cents"),
                "current_amount_cents": goal_data.get("current_amount_cents"),
                "remaining_cents": goal_data.get("target_amount_cents", 0) - goal_data.get("current_amount_cents", 0),
                "progress_percentage": progress_percentage,
                "target_date": goal_data.get("target_date"),
                "is_achieved": progress_percentage >= 100,
                "milestone_reached": progress_percentage >= 50 and progress_percentage < 75
            }
        }
        await manager.send_to_user(user_id, message)

    @staticmethod
    async def emit_goal_achieved(user_id: str, goal_data: Dict[str, Any]):
        """Emit goal achievement celebration"""
        message = {
            "type": MessageType.GOAL_ACHIEVED,
            "payload": {
                "goal_id": goal_data.get("id"),
                "goal_name": goal_data.get("name"),
                "target_amount_cents": goal_data.get("target_amount_cents"),
                "achieved_amount_cents": goal_data.get("current_amount_cents"),
                "achievement_date": datetime.utcnow().isoformat(),
                "celebration_message": f"🎉 Congratulations! You've achieved your '{goal_data.get('name')}' goal!",
                "priority": NotificationPriority.HIGH
            }
        }
        await manager.send_to_user(user_id, message)

    # ========== ACCOUNT EVENTS ==========
    
    @staticmethod
    async def emit_account_synced(user_id: str, account_id: str, sync_result: Dict[str, Any]):
        """Emit account sync completion"""
        message = {
            "type": MessageType.ACCOUNT_SYNCED,
            "payload": {
                "account_id": account_id,
                "account_name": sync_result.get("account_name"),
                "transactions_added": sync_result.get("transactions_added", 0),
                "balance_updated": sync_result.get("balance_updated", False),
                "new_balance_cents": sync_result.get("new_balance_cents"),
                "sync_duration_ms": sync_result.get("sync_duration_ms"),
                "synced_at": datetime.utcnow().isoformat(),
                "success": True
            }
        }
        await manager.send_to_user(user_id, message)

    @staticmethod
    async def emit_account_sync_error(user_id: str, account_id: str, error_details: Dict[str, Any]):
        """Emit account sync error"""
        message = {
            "type": MessageType.ACCOUNT_SYNC_ERROR,
            "payload": {
                "account_id": account_id,
                "account_name": error_details.get("account_name"),
                "error_message": error_details.get("error_message"),
                "error_code": error_details.get("error_code"),
                "retry_suggested": error_details.get("retry_suggested", True),
                "failed_at": datetime.utcnow().isoformat(),
                "priority": NotificationPriority.MEDIUM
            }
        }
        await manager.send_to_user(user_id, message)

    # ========== AI & INSIGHTS EVENTS ==========
    
    @staticmethod
    async def emit_ai_insight(user_id: str, insight_data: Dict[str, Any]):
        """Emit AI-generated financial insight"""
        message = {
            "type": MessageType.AI_INSIGHT_GENERATED,
            "payload": {
                "insight_id": insight_data.get("id"),
                "title": insight_data.get("title"),
                "description": insight_data.get("description"),
                "insight_type": insight_data.get("type"),  # spending_pattern, saving_opportunity, etc.
                "data": insight_data.get("data", {}),
                "confidence_score": insight_data.get("confidence_score"),
                "actionable": insight_data.get("actionable", False),
                "action_items": insight_data.get("action_items", []),
                "priority": insight_data.get("priority", NotificationPriority.MEDIUM),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        await manager.send_to_user(user_id, message)

    @staticmethod
    async def emit_spending_pattern_detected(user_id: str, pattern_data: Dict[str, Any]):
        """Emit detected spending pattern"""
        message = {
            "type": MessageType.SPENDING_PATTERN_DETECTED,
            "payload": {
                "pattern_type": pattern_data.get("type"),  # unusual_spending, recurring_expense, etc.
                "category": pattern_data.get("category"),
                "description": pattern_data.get("description"),
                "amount_cents": pattern_data.get("amount_cents"),
                "frequency": pattern_data.get("frequency"),
                "confidence": pattern_data.get("confidence"),
                "suggestion": pattern_data.get("suggestion"),
                "detected_at": datetime.utcnow().isoformat()
            }
        }
        await manager.send_to_user(user_id, message)

    # ========== NOTIFICATION EVENTS ==========
    
    @staticmethod
    async def emit_notification(
        user_id: str, 
        title: str, 
        message: str, 
        notification_type: str = "info",
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Emit generic notification"""
        notification_message = {
            "type": MessageType.NOTIFICATION,
            "payload": {
                "id": f"notif_{datetime.utcnow().timestamp()}",
                "title": title,
                "message": message,
                "notification_type": notification_type,  # success, error, warning, info
                "priority": priority,
                "action_url": action_url,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "read": False
            }
        }
        await manager.send_to_user(user_id, notification_message)

    @staticmethod
    async def emit_system_alert(
        user_ids: List[str], 
        alert_type: str, 
        message: str, 
        priority: NotificationPriority = NotificationPriority.HIGH
    ):
        """Emit system-wide alert to multiple users"""
        alert_message = {
            "type": MessageType.SYSTEM_ALERT,
            "payload": {
                "alert_type": alert_type,
                "message": message,
                "priority": priority,
                "system_wide": True,
                "created_at": datetime.utcnow().isoformat()
            }
        }
        await manager.broadcast_to_users(user_ids, alert_message)

    # ========== UTILITY METHODS ==========
    
    @staticmethod
    async def emit_multiple_events(user_id: str, events: List[Dict[str, Any]]):
        """Emit multiple events in a batch"""
        batch_message = {
            "type": "batch_update",
            "payload": {
                "events": events,
                "count": len(events),
                "batch_id": f"batch_{datetime.utcnow().timestamp()}"
            }
        }
        await manager.send_to_user(user_id, batch_message)

    @staticmethod
    async def emit_heartbeat(user_id: str):
        """Emit heartbeat to keep connection alive"""
        message = {
            "type": MessageType.PING,
            "payload": {
                "server_time": datetime.utcnow().isoformat(),
                "connection_status": "active"
            }
        }
        await manager.send_to_user(user_id, message, persist=False)