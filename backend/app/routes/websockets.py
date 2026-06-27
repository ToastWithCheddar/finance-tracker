# backend/app/routes/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query 
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
import asyncio
import logging
from datetime import datetime, timezone

from app.websocket.manager import redis_websocket_manager as manager
from app.websocket.events import WebSocketEvents, MessageType
from app.auth.dependencies import get_current_user_from_token, require_admin
from app.database import get_db
from app.models import User
from app.core.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
    AuthenticationError
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="(deprecated) JWT in querystring"),
    db: Session = Depends(get_db)
):
    """Main WebSocket endpoint for real-time updates.

    FE-SEC-001 / BE-SEC-007 hardening: accept the connection first, then
    require the client to send `{"type":"auth","token":"<jwt>"}` as the
    first frame. The legacy `?token=` querystring path is honoured for one
    release window so clients can roll forward, but should be removed.
    """
    user = None
    try:
        # We must accept() before we can receive frames.
        await websocket.accept()

        auth_token: Optional[str] = token
        if not auth_token:
            # Read first message — must be the auth handshake.
            try:
                first_frame = await asyncio.wait_for(
                    websocket.receive_json(), timeout=10.0
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.info(f"WS auth handshake failed (no/invalid first frame): {e}")
                await websocket.close(code=4401, reason="Auth handshake required")
                return

            if not isinstance(first_frame, dict) or first_frame.get("type") != "auth":
                await websocket.close(code=4401, reason="First frame must be auth")
                return
            auth_token = first_frame.get("token")
            if not isinstance(auth_token, str) or not auth_token:
                await websocket.close(code=4401, reason="Missing token in auth frame")
                return

        # Authenticate user from token (after accept()).
        try:
            user = await get_current_user_from_token(token=auth_token, db=db)
        except Exception as e:
            logger.info(f"WS token validation failed: {e}")
            await websocket.close(code=4401, reason="Authentication failed")
            return
        if not user:
            await websocket.close(code=4401, reason="Authentication failed")
            return

        logger.info(f"WebSocket connection attempt for user: {user.id}")

        # Collect connection metadata
        client_info = {
            "user_agent": websocket.headers.get("user-agent", ""),
            "client_ip": websocket.client.host if websocket.client else "unknown",
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
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
                    manager.connection_metadata[websocket]["last_activity"] = datetime.now(timezone.utc).isoformat()
                
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
        except Exception:
            # Socket may already be closed; nothing more we can do here.
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
        
        # Handle different message types (simplified)
        if message_type == "ping":
            await handle_ping(websocket, user_id, payload)
            
        elif message_type == "dashboard_refresh":
            await handle_dashboard_refresh(websocket, user_id, payload)
            
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
                "server_time": datetime.now(timezone.utc).isoformat(),
                "client_time": payload.get("client_time"),
                "latency_ms": payload.get("sent_at")
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_text(json.dumps(pong_message))
    except Exception as e:
        logger.error(f"Error sending pong to {user_id}: {str(e)}")

async def handle_dashboard_refresh(websocket: WebSocket, user_id: str, payload: Dict[str, Any]):
    """Handle dashboard refresh requests"""
    try:
        # Send fresh dashboard data
        await manager.send_full_sync(user_id, websocket)
        
    except Exception as e:
        logger.error(f"Error refreshing dashboard for {user_id}: {str(e)}")

async def send_error_response(websocket: WebSocket, error_message: str):
    """Send error response to client"""
    try:
        error_response = {
            "type": "error",
            "payload": {
                "message": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"WebSocket health check failed: {str(e)}", exc_info=True)
        raise ExternalServiceError("WebSocket Service", "WebSocket service unhealthy")

# Admin endpoint to get connection statistics
@router.get("/ws/stats")
async def get_websocket_stats(current_user: User = Depends(require_admin)):
    """Get detailed WebSocket connection statistics (admin only)"""
    try:
        stats = await manager.get_connection_stats()
        
        return {
            "statistics": stats,
            "manager_info": {
                "connected_users": manager.get_connected_users(),
                "total_connections": manager.get_total_connections()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
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
    current_user: User = Depends(require_admin)
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
    current_user: User = Depends(require_admin)
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

# --- Simple background cleanup task (dev-friendly) ---
async def cleanup_stale_connections(check_interval_seconds: int = 60, idle_minutes: int = 30):
    """
    Periodically scan connection metadata and disconnect sockets that appear idle.
    Minimal, safe no-op in development if metadata is missing.
    """
    try:
        while True:
            try:
                now = datetime.now(timezone.utc)
                threshold = now.timestamp() - idle_minutes * 60
                # Iterate a copy of metadata to avoid runtime mutation issues
                for ws, meta in list(manager.connection_metadata.items()):
                    last = meta.get("last_activity")
                    try:
                        last_ts = datetime.fromisoformat(last).timestamp() if isinstance(last, str) else now.timestamp()
                    except Exception:
                        last_ts = now.timestamp()
                    if last_ts < threshold:
                        try:
                            await manager.disconnect(ws)
                        except Exception:
                            pass
            except Exception:
                # Swallow errors; this is a best-effort cleanup in dev
                pass
            await asyncio.sleep(check_interval_seconds)
    except asyncio.CancelledError:
        # Task cancelled on shutdown
        return
