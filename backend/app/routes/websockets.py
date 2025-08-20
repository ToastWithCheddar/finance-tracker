# backend/app/routes/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query 
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

from ..websocket.manager import redis_websocket_manager as manager
from ..websocket.events import WebSocketEvents, MessageType
from ..auth.dependencies import get_current_user_from_token
from ..database import get_db
from ..models import User
from ..core.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
    AuthenticationError
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """Main WebSocket endpoint for real-time updates"""
    user = None
    try:
        # Authenticate user from token
        user = await get_current_user_from_token(token=token, db=db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return

        logger.info(f"WebSocket connection attempt for user: {user.id}")

        # Collect connection metadata
        client_info = {
            "user_agent": websocket.headers.get("user-agent", ""),
            "client_ip": websocket.client.host if websocket.client else "unknown",
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }

        # Connect to WebSocket manager
        await manager.connect(user.id, websocket, client_info)
        
        logger.info(f"WebSocket connected successfully for user: {user.id}")

        try:
            # Main message loop
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                # Update last activity
                if websocket in manager.connection_metadata:
                    manager.connection_metadata[websocket]["last_activity"] = datetime.utcnow().isoformat()
                
                # Handle incoming message
                await handle_client_message(websocket, user.id, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally for user: {user.id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user.id}: {str(e)}")
            await websocket.close(code=4000, reason="Internal server error")
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass
    finally:
        # Always cleanup connection
        if user:
            await manager.disconnect(websocket)

async def handle_client_message(websocket: WebSocket, user_id: str, message_data: str):
    """Handle incoming messages from WebSocket clients"""
    try:
        message = json.loads(message_data)
        message_type = message.get("type")
        payload = message.get("payload", {})
        
        logger.debug(f"Received WebSocket message from {user_id}: {message_type}")
        
        # Handle different message types
        if message_type == "ping":
            await handle_ping(websocket, user_id, payload)
            
        elif message_type == "subscribe":
            await handle_subscription(websocket, user_id, payload)
            
        elif message_type == "unsubscribe":
            await handle_unsubscription(websocket, user_id, payload)
            
        elif message_type == "dashboard_refresh":
            await handle_dashboard_refresh(websocket, user_id, payload)
            
        elif message_type == "mark_notification_read":
            await handle_mark_notification_read(websocket, user_id, payload)
            
        elif message_type == "get_connection_stats":
            await handle_get_connection_stats(websocket, user_id, payload)
            
        else:
            # Unknown message type
            await send_error_response(websocket, f"Unknown message type: {message_type}")
            
    except json.JSONDecodeError:
        await send_error_response(websocket, "Invalid JSON format")
    except Exception as e:
        logger.error(f"Error handling client message: {str(e)}")
        await send_error_response(websocket, "Message handling error")

async def handle_ping(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle ping messages from client"""
    try:
        pong_message = {
            "type": "pong",
            "payload": {
                "server_time": datetime.utcnow().isoformat(),
                "client_time": payload.get("client_time"),
                "latency_ms": payload.get("sent_at")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(pong_message))
    except Exception as e:
        logger.error(f"Error sending pong to {user_id}: {str(e)}")

async def handle_subscription(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle subscription requests"""
    try:
        subscription_types = payload.get("types", [])
        
        # Store subscription preferences in connection metadata
        if websocket in manager.connection_metadata:
            manager.connection_metadata[websocket]["subscriptions"] = subscription_types
        
        response = {
            "type": "subscription_confirmed",
            "payload": {
                "subscribed_types": subscription_types,
                "user_id": user_id
            }
        }
        await websocket.send_text(json.dumps(response))
        
        logger.info(f"User {user_id} subscribed to: {subscription_types}")
        
    except Exception as e:
        logger.error(f"Error handling subscription for {user_id}: {str(e)}")

async def handle_unsubscription(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle unsubscription requests"""
    try:
        unsubscribe_types = payload.get("types", [])
        
        # Update subscription preferences
        if websocket in manager.connection_metadata:
            current_subs = manager.connection_metadata[websocket].get("subscriptions", [])
            updated_subs = [sub for sub in current_subs if sub not in unsubscribe_types]
            manager.connection_metadata[websocket]["subscriptions"] = updated_subs
        
        response = {
            "type": "unsubscription_confirmed", 
            "payload": {
                "unsubscribed_types": unsubscribe_types,
                "remaining_subscriptions": updated_subs
            }
        }
        await websocket.send_text(json.dumps(response))
        
        logger.info(f"User {user_id} unsubscribed from: {unsubscribe_types}")
        
    except Exception as e:
        logger.error(f"Error handling unsubscription for {user_id}: {str(e)}")

async def handle_dashboard_refresh(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle dashboard refresh requests"""
    try:
        # Send fresh dashboard data
        await manager.send_full_sync(user_id, websocket)
        
        response = {
            "type": "dashboard_refresh_completed",
            "payload": {
                "refreshed_at": datetime.utcnow().isoformat()
            }
        }
        await websocket.send_text(json.dumps(response))
        
    except Exception as e:
        logger.error(f"Error refreshing dashboard for {user_id}: {str(e)}")

async def handle_mark_notification_read(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle marking notifications as read"""
    try:
        notification_ids = payload.get("notification_ids", [])
        
        # Here you could update notification status in database
        # For now, just acknowledge
        response = {
            "type": "notifications_marked_read",
            "payload": {
                "marked_read": notification_ids,
                "marked_at": datetime.utcnow().isoformat()
            }
        }
        await websocket.send_text(json.dumps(response))
        
        logger.debug(f"Marked {len(notification_ids)} notifications as read for {user_id}")
        
    except Exception as e:
        logger.error(f"Error marking notifications read for {user_id}: {str(e)}")

async def handle_get_connection_stats(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle connection statistics requests"""
    try:
        stats = await manager.get_connection_stats()
        user_connections = manager.get_user_connection_count(user_id)
        
        response = {
            "type": "connection_stats",
            "payload": {
                "user_connections": user_connections,
                "total_connections": stats.get("active_connections", 0),
                "connected_users": stats.get("connected_users", 0),
                "server_uptime": datetime.utcnow().isoformat()
            }
        }
        await websocket.send_text(json.dumps(response))
        
    except Exception as e:
        logger.error(f"Error getting connection stats for {user_id}: {str(e)}")

async def send_error_response(websocket: WebSocket, error_message: str):
    """Send error response to client"""
    try:
        error_response = {
            "type": "error",
            "payload": {
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await websocket.send_text(json.dumps(error_response))
    except Exception as e:
        logger.error(f"Error sending error response: {str(e)}")

# Health check endpoint for WebSocket service
@router.get("/ws/health")
async def websocket_health():
    """Health check for WebSocket service"""
    try:
        stats = await manager.get_connection_stats()
        return {
            "status": "healthy",
            "total_connections": stats.get("active_connections", 0),
            "connected_users": stats.get("connected_users", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"WebSocket health check failed: {str(e)}", exc_info=True)
        raise ExternalServiceError("WebSocket Service", "WebSocket service unhealthy")

# Admin endpoint to get connection statistics
@router.get("/ws/stats")
async def get_websocket_stats(current_user: User = Depends(get_current_user_from_token)):
    """Get detailed WebSocket connection statistics (admin only)"""
    try:
        stats = await manager.get_connection_stats()
        
        return {
            "statistics": stats,
            "manager_info": {
                "connected_users": manager.get_connected_users(),
                "total_connections": manager.get_total_connections()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {str(e)}", exc_info=True)
        raise ExternalServiceError("WebSocket Service", "Failed to get WebSocket statistics")

# Endpoint to send test message to user (for testing)
@router.post("/ws/test-message/{user_id}")
async def send_test_message(
    user_id: str,
    message_type: str,
    message_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_from_token)
):
    """Send test message to a user (for testing purposes)"""
    try:
        if not manager.is_user_connected(user_id):
            raise ResourceNotFoundError("Connected user", user_id)
        
        test_message = {
            "type": message_type,
            "payload": {
                **message_data,
                "test_message": True,
                "sent_by": current_user.id
            }
        }
        
        await manager.send_to_user(user_id, test_message)
        
        return {
            "success": True,
            "message": f"Test message sent to user {user_id}",
            "message_type": message_type
        }
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error sending test message: {str(e)}", exc_info=True)
        raise ExternalServiceError("WebSocket Service", "Failed to send test message")

# Endpoint to broadcast system message
@router.post("/ws/broadcast")
async def broadcast_system_message(
    message_type: str,
    message_data: Dict[str, Any],
    priority: str = "medium",
    current_user: User = Depends(get_current_user_from_token)
):
    """Broadcast system message to all connected users (admin only)"""
    try:
        system_message = {
            "type": message_type,
            "payload": {
                **message_data,
                "system_broadcast": True,
                "priority": priority,
                "broadcast_by": current_user.id
            }
        }
        
        await manager.broadcast_to_all(system_message)
        
        connected_users = len(manager.get_connected_users())
        
        return {
            "success": True,
            "message": f"System message broadcasted to {connected_users} users",
            "message_type": message_type,
            "recipients": connected_users
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting system message: {str(e)}", exc_info=True)
        raise ExternalServiceError("WebSocket Service", "Failed to broadcast system message")

# Background task to cleanup stale connections
async def cleanup_stale_connections():
    """Background task to periodically cleanup stale connections"""
    while True:
        try:
            await manager.cleanup_stale_connections()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

# Start cleanup task when module is imported
try:
    asyncio.create_task(cleanup_stale_connections())
except RuntimeError:
    # Handle case where event loop is not yet running
    logger.info("Event loop not ready, cleanup task will be started later")