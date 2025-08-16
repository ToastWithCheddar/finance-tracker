# Real-time Systems

This document describes the Redis-based real-time architecture of the application, implementing scalable WebSocket communication.

## 1. Redis-Based Real-time Architecture Overview

The application uses a Redis pub/sub system with WebSockets for scalable real-time communication between the frontend and backend. This architecture ensures message persistence, supports multiple backend instances, and provides reliable message delivery.

```
┌─────────────────────────────────────────────────────────────┐
│                 REDIS-BASED REAL-TIME SYSTEM               │
├─────────────────────────────────────────────────────────────┤
│  Frontend WebSocket Clients                                 │
│       ↕ (WebSocket connections)                            │
│  Backend WebSocket Endpoints                               │
│       ↕ (Redis Pub/Sub channels)                          │
│  Redis Message Broker                                      │
│  ├── User-specific channels: ws:user:{user_id}             │
│  ├── Broadcast channel: ws:broadcast                       │
│  └── Message persistence: notifications:{user_id}          │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

*   **Redis Client (`backend/app/core/redis_client.py`):** Manages Redis connections, pub/sub messaging, and message persistence
*   **Redis WebSocket Manager (`backend/app/websocket/manager_redis.py`):** Handles WebSocket connections using Redis for message broadcasting
*   **WebSocket Events (`backend/app/websocket/events.py`):** Publishes real-time events to Redis channels
*   **Frontend `useWebSocket` Hook:** Connects to WebSocket endpoints and handles incoming messages
*   **Zustand `realtimeStore`:** Manages WebSocket connection state and real-time data

### Architecture Benefits

*   **Scalability:** Multiple backend instances can share Redis for consistent messaging
*   **Persistence:** Messages are stored in Redis for offline users and reconnection scenarios  
*   **Reliability:** Redis pub/sub ensures message delivery across server restarts
*   **Performance:** Optimized Redis connections with connection pooling and health checks

## 2. Redis Pub/Sub Message Flow

### Message Publishing Flow
1. **Backend Service Event:** A service (e.g., TransactionService) creates/updates data
2. **WebSocket Event Emission:** The service calls `WebSocketEvents.emit_*()` method
3. **Redis Publishing:** The event is published to the user-specific Redis channel `ws:user:{user_id}`
4. **Message Persistence:** Message is stored in Redis list `notifications:{user_id}` for offline recovery

### Message Consumption Flow  
1. **WebSocket Connection:** User connects to `/ws` endpoint with authentication
2. **Redis Subscriber:** Backend starts a Redis subscriber task for the user's channel
3. **Message Relay:** Subscriber receives messages from Redis and forwards to WebSocket
4. **Frontend Processing:** Frontend receives real-time updates via WebSocket

### Redis Channels
*   **User-specific channels:** `ws:user:{user_id}` - Individual user messages
*   **Broadcast channel:** `ws:broadcast` - System-wide announcements
*   **Notification persistence:** `notifications:{user_id}` - Message storage for offline users

## 3. WebSocket Endpoints

### Main WebSocket Endpoint
*   **Endpoint:** `/ws` (with JWT token authentication via query parameter)
*   **File:** `backend/app/routes/websockets.py`
*   **Features:**
    - JWT-based authentication
    - Automatic Redis subscriber management
    - Connection metadata tracking
    - Heartbeat/ping-pong support
    - Graceful disconnection handling

### Health Check Endpoints
*   **`/ws/health`** - WebSocket service health status
*   **`/ws/stats`** - Detailed connection statistics (admin only)

### Testing Endpoints  
*   **`/ws/test-message/{user_id}`** - Send test messages to specific users
*   **`/ws/broadcast`** - Broadcast system messages to all users

## 4. Real-time Event Types

### Transaction Events
*   **`NEW_TRANSACTION`** - New transaction created
*   **`TRANSACTION_UPDATED`** - Transaction modified
*   **`TRANSACTION_DELETED`** - Transaction deleted
*   **`BULK_TRANSACTIONS_IMPORTED`** - Multiple transactions imported

### Budget Events
*   **`BUDGET_ALERT`** - Budget threshold warnings and exceeded notifications
*   **`BUDGET_UPDATED`** - Budget modifications

### Goal Events
*   **`GOAL_PROGRESS_UPDATE`** - Goal progress changes
*   **`GOAL_ACHIEVED`** - Goal completion celebrations

### Account Events
*   **`ACCOUNT_SYNCED`** - Successful account synchronization
*   **`ACCOUNT_SYNC_ERROR`** - Account sync failures
*   **`BALANCE_UPDATE`** - Account balance changes

### AI & Insights Events
*   **`AI_INSIGHT_GENERATED`** - AI-generated financial insights
*   **`SPENDING_PATTERN_DETECTED`** - Unusual spending patterns

### Dashboard Events
*   **`DASHBOARD_UPDATE`** - Complete dashboard state refresh
*   **`FULL_SYNC`** - Initial connection data synchronization

### System Events
*   **`NOTIFICATION`** - General notifications
*   **`SYSTEM_ALERT`** - System-wide alerts
*   **`PING/PONG`** - Connection heartbeat