# backend/app/websocket/manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any, Set
import asyncio
import json
from datetime import datetime, timedelta
import uuid 
import logging

from .schemas import TypedWebSocketMessage, validate_websocket_message 
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


class RedisWebSocketManager:
    """Redis-based WebSocket manager for scalable real-time messaging"""
    
    def __init__(self):
        # In-memory connection tracking - only for active WebSocket connections
        # This is local to each backend instance and only tracks active connections
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.connection_user_map: Dict[WebSocket, str] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

        # Redis client for pub/sub messaging and persistence
        self.redis_client = redis_client

        # Connection tracking for statistics
        self.total_connections_count = 0
        self.connection_start_time = datetime.utcnow()
        
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
            
            # Send any missed notifications
            await self.send_missed_notifications(user_id, websocket)
            
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
            # Validate and enrich message
            enriched_message = await self._prepare_message(user_id, message)
            
            # Persist message if requested
            if persist:
                await self.redis_client.persist_message(user_id, enriched_message)
            
            # Publish to Redis channel for this user
            success = await self.redis_client.publish_to_user(user_id, enriched_message)
            
            if not success:
                logger.warning(f"Failed to publish message to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {str(e)}")

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
            from ..services.analytics_service import analytics_service
            from ..database import get_db

            # Get dashboard data
            db = next(get_db())
            dashboard_data = await analytics_service.get_dashboard_summary(db, user_id)

            sync_message = {
                "type": "full_sync",
                "payload": dashboard_data,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Send directly to the specific WebSocket (not via Redis)
            await websocket.send_text(json.dumps(sync_message))
            logger.debug(f"Sent full sync to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending full sync to user {user_id}: {str(e)}")

    async def send_missed_notifications(self, user_id: str, websocket: WebSocket):
        """Send missed notifications directly to a specific WebSocket"""
        try:
            # Get missed messages from Redis
            missed_messages = await self.redis_client.get_missed_messages(user_id, limit=20)
            
            # Filter messages that are less than 1 hour old
            current_time = datetime.utcnow()
            recent_messages = []
            
            for message in missed_messages:
                try:
                    msg_time = datetime.fromisoformat(message.get("timestamp", ""))
                    if current_time - msg_time < timedelta(hours=1):
                        recent_messages.append(message)
                except ValueError:
                    continue
            
            # Send each recent message
            for message in recent_messages:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending missed notification: {str(e)}")
                    
            if recent_messages:
                logger.debug(f"Sent {len(recent_messages)} missed notifications to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending missed notifications to user {user_id}: {str(e)}")

    async def _start_user_subscriber(self, user_id: str):
        """Start Redis subscriber task for a user"""
        if user_id in self.subscriber_tasks:
            return  # Already running
            
        try:
            channel = f"ws:user:{user_id}"
            task = asyncio.create_task(
                self._user_message_subscriber(user_id, channel),
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

    async def _user_message_subscriber(self, user_id: str, channel: str):
        """Redis subscriber task for a specific user"""
        async def message_handler(message: Dict[str, Any]):
            """Handle incoming message from Redis"""
            try:
                # Send message to all WebSocket connections for this user
                if user_id in self.connections:
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
                logger.error(f"Error handling message for user {user_id}: {str(e)}")

        async def error_handler(error: Exception):
            """Handle subscriber errors"""
            logger.error(f"Subscriber error for user {user_id}: {str(error)}")

        try:
            await self.redis_client.subscribe(channel, message_handler, error_handler)
        except asyncio.CancelledError:
            logger.debug(f"Subscriber task cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Subscriber task error for user {user_id}: {str(e)}")

    async def _prepare_message(self, user_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate message for sending"""
        try:
            # Validate message structure
            typed_message = validate_websocket_message(message)
            return typed_message.model_dump()
            
        except Exception as e:
            logger.error(f"Error validating message: {str(e)}")
            # Fallback to basic message format
            return {
                **message,
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
            }

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
                "uptime_seconds": (datetime.utcnow() - self.connection_start_time).total_seconds(),
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

    async def cleanup_stale_connections(self):
        """Clean up stale connections and old messages"""
        try:
            # Clean up old messages in Redis
            await self.redis_client.cleanup_old_messages(max_age_hours=24)
            
            # Check for stale WebSocket connections
            stale_connections = []
            current_time = datetime.utcnow()
            
            for websocket, user_id in self.connection_user_map.items():
                try:
                    metadata = self.connection_metadata.get(websocket, {})
                    last_activity = metadata.get("last_activity")
                    
                    if last_activity:
                        last_activity_time = datetime.fromisoformat(last_activity)
                        if (current_time - last_activity_time).total_seconds() > 3600:  # 1 hour
                            stale_connections.append(websocket)
                            
                except Exception as e:
                    logger.warning(f"Error checking connection staleness: {str(e)}")
                    stale_connections.append(websocket)
            
            # Disconnect stale connections
            for websocket in stale_connections:
                try:
                    await self.disconnect(websocket)
                    logger.info("Cleaned up stale WebSocket connection")
                except Exception as e:
                    logger.error(f"Error cleaning up stale connection: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

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