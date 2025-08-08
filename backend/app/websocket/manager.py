from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any, Set
import asyncio
import json
import redis
from datetime import datetime, timedelta
import uuid 
import logging

from .schemas import TypedWebSocketMessage, validate_websocket_message 

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # In-memory connection tracking 
        # Maps user_id -> set of websockets connections (users can have multiple devices)
        self.connections: Dict[str, Set[WebSocket]] = {}
        # Reverse mapping of websocket -> user_id for quick lookup
        self.connection_user_map: Dict[WebSocket, str] = {}
        # Store additional connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

        # The user_id here connects to your authentication system - each WebSocket is tied to an authenticated user.
        # Redis for persistence memory and recovery
        self.redis = redis.Redis(host="localhost", port=6379, db=0)

        # Message tracking for deduplication (using set specifically for uniqueness)
        self.message_tracking: Set[str] = set()

    async def connect(self, user_id: str, websocket: WebSocket, metadata: Dict[str, Any] = None):
        """Accepts and stores a new websocket connection for a user"""
        try: 
            # Establish the connection
            await websocket.accept()

            # Add new user to the connections dictionary
            if user_id not in self.connections:
                self.connections[user_id] = set()

            # User already in the connections set, add the connection new websocket
            self.connections[user_id].add(websocket)
            self.connection_user_map[websocket] = user_id
            self.connection_metadata[websocket] = metadata or {}

            # Send full sync on the connect 
            # Send complete dashboard state immediately
            await self.send_full_sync(user_id, websocket)

            # Send any missed notifications
            await self.send_notifications(user_id, websocket)

            # Send any missed messages
            await self.send_messages(user_id, websocket)

        except Exception as e:
            logger.error(f"Error accepting websocket connection: {user_id} - {str(e)}")
            raise

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Removes a websocket connection and clean up"""
        if websocket in self.connection_user_map:
            user_id = self.connection_user_map[websocket]

            # Remove from the users connections set
            if user_id in self.connections:
                self.connections[user_id].discard(websocket)

                # Memory leaks prevention
                if not self.connections[user_id]:
                    del self.connections[user_id]

                # Is it logical to remove the websocket, user_id pair from the connection_user_map?
                # Remove from the connection_user_map
                if websocket in self.connection_user_map:
                    del self.connection_user_map[websocket]

    async def send_message(self, user_id: str, message: Dict[str, Any], persist: bool = True):
        """Send message to all connections of a specific user"""
        try:
            # Validate message structure
            typed_message = validate_websocket_message(message)
            
            # Convert to JSON for transmission
            message_json = typed_message.model_dump_json()
            
            # Send to all user connections
            if user_id in self.connections:
                disconnected_sockets = []
                for websocket in self.connections[user_id].copy():
                    try:
                        await websocket.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error sending message to websocket: {str(e)}")
                        disconnected_sockets.append(websocket)
                
                # Clean up disconnected sockets
                for websocket in disconnected_sockets:
                    self.disconnect(user_id, websocket)
            
            # Persist message if requested
            if persist:
                await self.persist_message(user_id, typed_message.model_dump())
                
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            # Fallback to untyped message
            enriched_message = {
                **message,
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
            }
            
            if persist:
                await self.persist_message(user_id, enriched_message)
            
    async def persist_message(self, user_id: str, message: Dict[str, Any]):
        """Persist message to redis"""
        try:
            key = f"notifications:{user_id}"

            # Store last 100 notifications per user 
            # Redis List: FIFO queue of messages per user
            # Thread executor to avoid blocking the main event loop
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.lpush(key, json.dumps(message))
            )
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.redis.ltrim(key, 0, 99)
            )

            # Cleanup old messages after 7 days
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.expire(key, 7 * 24 * 3600)
            )

        except Exception as e:
            logger.error(f"Error persisting message: {str(e)}")


    async def send_missed_notifications(self, user_id: str, websocket: WebSocket):
        """Send missed notifications that user missed while offlien"""
        try:
            key = f"notifications:{user_id}"

            # Get last 20 notifications
            # Thread executor to avoid blocking the main event loop
            notifications = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.redis.lrange(key, 0, 19)
            )

            if notifications:
                # Send in reverse order to maintain chronological order
                for notification in reversed(notifications):
                    try:
                        notification_data = json.loads(notification)
                        # Only send if the message is less than 1 hours old
                        msg_time = datetime.fromisoformat(notification_data["timestamp"])
                        if datetime.now() - msg_time < timedelta(hours=1):
                            await websocket.send_text(notification_data["message"])
                            
                    except Exception as e:
                        logger.error(f"Error sending missed notification: {str(e)}")

        except Exception as e:
            logger.error(f"Error retrieving missed notifications: {str(e)}")

    async def send_full_sync(self, user_id: str, websocket: WebSocket):
        """Send full sync of the dashboard state"""
        try:
            from ..services.dashboard_service import DashboardService
            from ..database import get_db

            # Get the dashboard state from the database
            db = next(get_db())
            dashboard_service = DashboardService(db)
            dashboard_data = await dashboard_service.get_dashboard_data(user_id)

            sync_message = {
                "type": "full_sync",
                "payload": dashboard_data,
                "timestamp": datetime.now().isoformat(),
            }

            await websocket.send_text(json.dumps(sync_message))

        except Exception as e:
            logger.error(f"Error sending full sync: {str(e)}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any], persist: bool = True):
        """Alias for send_message for backward compatibility"""
        await self.send_message(user_id, message, persist)
    
    async def broadcast_to_users(self, user_ids: List[str], message: Dict[str, Any]):
        """Broadcast message to multiple users"""
        for user_id in user_ids:
            await self.send_to_user(user_id, message)
    
    async def send_notifications(self, user_id: str, websocket: WebSocket):
        """Alias for send_missed_notifications"""
        await self.send_missed_notifications(user_id, websocket)
    
    async def send_messages(self, user_id: str, websocket: WebSocket):
        """Send any missed messages (currently same as notifications)"""
        await self.send_missed_notifications(user_id, websocket)
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active WebSocket connections"""
        return user_id in self.connections and len(self.connections[user_id]) > 0


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
