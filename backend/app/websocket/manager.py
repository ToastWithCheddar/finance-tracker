# backend/app/websocket/manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any, Set
import asyncio
import json
from datetime import datetime, timezone
import uuid 
import logging

from .schemas import TypedWebSocketMessage, validate_websocket_message 
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class RedisWebSocketManager:
    """Simplified Redis-based WebSocket manager for basic real-time messaging"""
    
    def __init__(self):
        # In-memory connection tracking - only for active WebSocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.connection_user_map: Dict[WebSocket, str] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

        # Redis client for pub/sub messaging
        self.redis_client = redis_client

        # Connection tracking for statistics
        self.total_connections_count = 0
        self.connection_start_time = datetime.now(timezone.utc)
        
        # Active subscriber tasks for cleanup
        self.subscriber_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, user_id: str, websocket: WebSocket, metadata: Dict[str, Any] = None):
        """Accept and register a new WebSocket connection for a user"""
        try:
            # Accept the WebSocket connection
            await websocket.accept()
            
            # Add to local connection tracking
            if user_id not in self.connections:
                self.connections[user_id] = set()
                
            self.connections[user_id].add(websocket)
            self.connection_user_map[websocket] = user_id
            self.connection_metadata[websocket] = metadata or {}
            self.total_connections_count += 1
            
            logger.info(f"WebSocket connected for user {user_id}. Total connections: {len(self.connection_user_map)}")
            
            # Send initial sync data
            await self.send_full_sync(user_id, websocket)
            
            # Start subscriber for this user if not already running
            await self._start_user_subscriber(user_id)
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket for user {user_id}: {str(e)}")
            raise

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and clean up"""
        try:
            user_id = self.connection_user_map.get(websocket)
            
            if user_id and user_id in self.connections:
                # Remove from connections
                self.connections[user_id].discard(websocket)
                
                # Clean up empty user connection sets
                if not self.connections[user_id]:
                    del self.connections[user_id]
                    
                    # Stop subscriber task for this user if no more connections
                    await self._stop_user_subscriber(user_id)
            
            # Remove from reverse mapping and metadata
            if websocket in self.connection_user_map:
                del self.connection_user_map[websocket]
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
                
            logger.info(f"WebSocket disconnected for user {user_id}. Remaining connections: {len(self.connection_user_map)}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {str(e)}")

    async def send_to_user(self, user_id: str, message: Dict[str, Any], persist: bool = True):
        """Send message to a user via Redis pub/sub"""
        try:
            # Prepare message with basic enrichment
            enriched_message = await self._prepare_message(user_id, message)
            
            # Publish to user channel
            channel = f"ws:user:{user_id}"
            success = await self.redis_client.publish(channel, enriched_message)
            
            if not success:
                logger.warning(f"Failed to publish message to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {str(e)}")

    async def send_user_event(self, user_id: str, event, persist: bool = True):
        """Send WebSocketEvent to a user (compatibility method for TransactionSyncService)"""
        try:
            # Ensure user_id is a string (convert UUID if needed)
            user_id_str = str(user_id)
            
            # Convert WebSocketEvent to proper TypedWebSocketMessage format
            if hasattr(event, 'type') and hasattr(event, 'data'):
                # Convert WebSocketEvent to TypedWebSocketMessage format
                event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
                
                # Ensure all UUIDs are converted to strings to avoid JSON serialization errors
                sanitized_data = self._sanitize_data_for_json(event.data)
                
                message = {
                    "id": f"event_{datetime.now(timezone.utc).timestamp()}_{user_id_str}",
                    "type": event_type,
                    "timestamp": datetime.now(timezone.utc),
                    "user_id": user_id_str,
                    "payload": sanitized_data
                }
            elif hasattr(event, 'to_dict'):
                # Handle objects with to_dict method
                base_message = event.to_dict()
                sanitized_data = self._sanitize_data_for_json(base_message.get('data', {}))
                
                message = {
                    "id": f"event_{datetime.now(timezone.utc).timestamp()}_{user_id_str}",
                    "type": base_message.get('type', 'unknown'),
                    "timestamp": datetime.now(timezone.utc),
                    "user_id": user_id_str,
                    "payload": sanitized_data
                }
            else:
                # Fallback for other event formats
                sanitized_data = self._sanitize_data_for_json(event if isinstance(event, dict) else {"data": event})
                
                message = {
                    "id": f"event_{datetime.now(timezone.utc).timestamp()}_{user_id_str}",
                    "type": "unknown",
                    "timestamp": datetime.now(timezone.utc),
                    "user_id": user_id_str,
                    "payload": sanitized_data
                }
            
            # Sanitize the entire message structure before sending
            sanitized_message = self._sanitize_data_for_json(message)
            
            # Send via existing send_to_user method
            await self.send_to_user(user_id_str, sanitized_message, persist)
            
        except Exception as e:
            logger.error(f"Error sending user event to {user_id}: {str(e)}")

    def _sanitize_data_for_json(self, data: Any) -> Any:
        """Recursively sanitize data to ensure JSON serializability"""
        if data is None:
            return None
        elif isinstance(data, (str, int, float, bool)):
            return data
        elif hasattr(data, '__str__') and hasattr(data, 'hex'):  # UUID-like objects
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self._sanitize_data_for_json(value) for key, value in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_data_for_json(item) for item in data]
        else:
            # Fallback: convert to string
            return str(data)

    async def broadcast_to_users(self, user_ids: List[str], message: Dict[str, Any], persist: bool = True):
        """Send message to multiple users"""
        for user_id in user_ids:
            await self.send_to_user(user_id, message, persist)

    async def broadcast_to_all(self, message: Dict[str, Any], persist: bool = False):
        """Broadcast message to all connected users"""
        try:
            enriched_message = await self._prepare_message("system", message)
            
            # Publish to global broadcast channel
            success = await self.redis_client.publish_to_all_users(enriched_message)
            
            if not success:
                logger.warning("Failed to publish broadcast message")
                
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")

    async def send_full_sync(self, user_id: str, websocket: WebSocket):
        """Send complete dashboard state to a specific WebSocket connection"""
        try:
            from ..services.financial_health_service import get_financial_health_service
            from ..database import get_db
            from datetime import datetime, timedelta
            from ..models.transaction import Transaction
            from ..models.account import Account

            # Build snapshot using FinancialHealthService
            db = next(get_db())
            
            # Get recent transactions count
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_transactions = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= thirty_days_ago.date()
            ).count()
            
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).all()
            account_count = len(accounts)

            health_service = get_financial_health_service()
            financial_health = health_service.calculate_user_financial_health(db, user_id)

            dashboard_data = {
                "net_worth": financial_health.get("net_worth", 0),
                "total_liquid": financial_health.get("total_liquid", 0),
                "total_debt": financial_health.get("total_debt", 0),
                "total_investment": financial_health.get("total_investment", 0),
                "financial_health_score": financial_health.get("overall_score", 0),
                "financial_health_grade": financial_health.get("grade", "N/A"),
                "account_count": account_count,
                "recent_transactions": recent_transactions,
                "recommendations": financial_health.get("recommendations", []),
            }

            sync_message = {
                "type": "full_sync",
                "payload": dashboard_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Send directly to the specific WebSocket (not via Redis)
            await websocket.send_text(json.dumps(sync_message))
            logger.debug(f"Sent full sync to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending full sync to user {user_id}: {str(e)}")

    async def _start_user_subscriber(self, user_id: str):
        """Start Redis subscriber task for a user"""
        if user_id in self.subscriber_tasks:
            return  # Already running
            
        try:
            task = asyncio.create_task(
                self._user_message_subscriber(user_id),
                name=f"subscriber_{user_id}"
            )
            self.subscriber_tasks[user_id] = task
            logger.debug(f"Started Redis subscriber for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error starting subscriber for user {user_id}: {str(e)}")

    async def _stop_user_subscriber(self, user_id: str):
        """Stop Redis subscriber task for a user"""
        if user_id in self.subscriber_tasks:
            try:
                task = self.subscriber_tasks[user_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.subscriber_tasks[user_id]
                logger.debug(f"Stopped Redis subscriber for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error stopping subscriber for user {user_id}: {str(e)}")

    async def _user_message_subscriber(self, user_id: str):
        """Simple Redis subscriber task for a user"""
        async def handle_message(message: Dict[str, Any]):
            """Handle incoming message from Redis"""
            try:
                if user_id in self.connections and self.connections[user_id]:
                    disconnected_sockets = []
                    message_json = json.dumps(message)
                    for websocket in self.connections[user_id].copy():
                        try:
                            await websocket.send_text(message_json)
                        except Exception as e:
                            logger.error(f"Error sending message to WebSocket: {str(e)}")
                            disconnected_sockets.append(websocket)
                    
                    # Clean up disconnected sockets
                    for websocket in disconnected_sockets:
                        await self.disconnect(websocket)
            except Exception as e:
                logger.error(f"Error handling message for {user_id}: {str(e)}")

        async def error_handler(error: Exception):
            logger.error(f"Subscriber error for user {user_id}: {str(error)}")

        channel = f"ws:user:{user_id}"

        try:
            await self.redis_client.subscribe(channel, handle_message, error_handler)
        except asyncio.CancelledError:
            logger.debug(f"Subscriber task cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Subscriber task error for user {user_id}: {str(e)}")

    async def _prepare_message(self, user_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate message for sending"""
        try:
            # Ensure user_id is a string and sanitize the entire message before validation
            user_id_str = str(user_id)
            sanitized_message = self._sanitize_data_for_json(message)
            
            # Ensure the message has the required fields for validation
            if "user_id" not in sanitized_message:
                sanitized_message["user_id"] = user_id_str
            if "id" not in sanitized_message:
                sanitized_message["id"] = str(uuid.uuid4())
            if "timestamp" not in sanitized_message:
                sanitized_message["timestamp"] = datetime.now(timezone.utc)
                
            # Validate message structure
            typed_message = validate_websocket_message(sanitized_message)
            return typed_message.model_dump()
            
        except Exception as e:
            logger.error(f"Error validating message: {str(e)}")
            # Fallback to basic message format with sanitized data
            sanitized_fallback = self._sanitize_data_for_json({
                **message,
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": str(user_id),
            })
            return sanitized_fallback

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active WebSocket connections"""
        return user_id in self.connections and len(self.connections[user_id]) > 0

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user"""
        return len(self.connections.get(user_id, set()))

    def get_connected_users(self) -> List[str]:
        """Get list of all connected user IDs"""
        return list(self.connections.keys())

    def get_total_connections(self) -> int:
        """Get total number of active WebSocket connections"""
        return len(self.connection_user_map)

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        try:
            redis_stats = await self.redis_client.get_connection_stats()
            
            return {
                "active_connections": self.get_total_connections(),
                "connected_users": len(self.get_connected_users()),
                "total_connections_since_start": self.total_connections_count,
                "uptime_seconds": (datetime.now(timezone.utc) - self.connection_start_time).total_seconds(),
                "active_subscribers": len(self.subscriber_tasks),
                "redis_stats": redis_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting connection stats: {str(e)}")
            return {
                "active_connections": self.get_total_connections(),
                "connected_users": len(self.get_connected_users()),
                "error": str(e)
            }

    async def shutdown(self):
        """Shutdown the WebSocket manager and cleanup resources"""
        try:
            # Cancel all subscriber tasks
            for user_id in list(self.subscriber_tasks.keys()):
                await self._stop_user_subscriber(user_id)
            
            # Disconnect all WebSocket connections
            for websocket in list(self.connection_user_map.keys()):
                try:
                    await websocket.close(code=1001, reason="Server shutdown")
                except Exception:
                    pass
                await self.disconnect(websocket)
            
            # Close Redis client
            await self.redis_client.close()
            
            logger.info("WebSocket manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during WebSocket manager shutdown: {str(e)}")


# Global Redis-based WebSocket manager instance
redis_websocket_manager = RedisWebSocketManager()
