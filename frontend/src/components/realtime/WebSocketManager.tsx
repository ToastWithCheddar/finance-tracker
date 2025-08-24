import React from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

export function WebSocketManager() {
  const ENABLE_REALTIME = import.meta.env.VITE_ENABLE_REALTIME !== 'false';
  // Establish a single global WebSocket connection for the app
  useWebSocket({ autoConnect: ENABLE_REALTIME });
  return null;
}

export default WebSocketManager;

