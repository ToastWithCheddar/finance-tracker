# Real-time Systems

This document describes the real-time architecture of the application, based on the current state of the codebase.

## 1. Real-time Architecture Overview

The application uses WebSockets for real-time communication between the frontend and backend.

![Real-time Architecture Diagram](./images/real-time-architecture.png)
*Figure 4: Real-time System Architecture*

### Key Components

*   **FastAPI WebSocket Endpoints:** The backend exposes WebSocket endpoints for real-time communication.
*   **`useWebSocket` Hook:** The frontend uses a custom `useWebSocket` hook to connect to the WebSocket endpoints and handle incoming messages.
*   **Zustand `realtimeStore`:** The `realtimeStore` is used to manage the state of the WebSocket connection and the real-time data.

## 2. WebSocket Endpoints

*   The backend exposes a WebSocket endpoint at `/ws`.
*   The `backend/app/routes/websockets.py` file contains the logic for handling WebSocket connections.

## 3. Real-time Events

The `frontend/src/types/websocket.ts` file defines the types for the WebSocket events.

*   **`TRANSACTION_UPDATED`**: Sent when a transaction is updated.
*   **`BUDGET_UPDATED`**: Sent when a budget is updated.
*   **`GOAL_UPDATED`**: Sent when a goal is updated.