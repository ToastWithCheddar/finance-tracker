import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { useAuthStore } from '../stores/authStore';
import { useRealtimeStore } from '../stores/realtimeStore';
import { secureStorage } from '../services/secureStorage';

const WEBSOCKET_URL_BASE = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws';

export interface WebSocketMessage {
  type: string;
  payload: any;
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
}

interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  subscribe?: (callback: (message: WebSocketMessage) => void) => () => void;
  refreshDashboard: () => void;
}

export function useWebSocket(options?: UseWebSocketOptions): WebSocketState {
  const queryClient = useQueryClient();
  const { user, isAuthenticated } = useAuthStore();
  const { handleWebSocketMessage, updateConnectionStatus } = useRealtimeStore();
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Get token from secure storage
  const accessToken = secureStorage.getAccessToken();

  const refreshDashboard = () => {
    // Invalidate dashboard queries to trigger a refetch
    queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
    queryClient.invalidateQueries({ queryKey: ['accounts'] });
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
  };

  useEffect(() => {
    if (!isAuthenticated || !user?.id || !accessToken) {
      // If not authenticated, ensure any existing connection is closed
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setIsConnected(false);
      setIsConnecting(false);
      return;
    }

    // Avoid creating a new connection if one already exists
    if (socketRef.current) {
      return;
    }

    const connect = () => {
      setIsConnecting(true);
      const socketUrl = `${WEBSOCKET_URL_BASE}?token=${accessToken}`;
      const socket = new WebSocket(socketUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('🔌 WebSocket connection established');
        setIsConnected(true);
        setIsConnecting(false);
        updateConnectionStatus('connected');
        toast.info('Real-time updates connected.');
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('📬 WebSocket message received:', message);

          // Call custom onMessage handler if provided
          if (options?.onMessage) {
            options.onMessage(message);
          }

          // Use RealtimeStore's comprehensive message handler
          handleWebSocketMessage(message);

          // Legacy fallback for old message formats
          if (message.type === 'DASHBOARD_UPDATE' && message.data?.event === 'sync_completed') {
            toast.success('Bank sync complete! Refreshing dashboard...');
            refreshDashboard();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      socket.onclose = (event) => {
        console.log('🔌 WebSocket connection closed:', event.code, event.reason);
        socketRef.current = null;
        setIsConnected(false);
        setIsConnecting(false);
        updateConnectionStatus('disconnected');
        
        // Optional: implement a reconnect strategy
        if (!event.wasClean) {
          toast.warning('Real-time connection lost. Attempting to reconnect...');
          updateConnectionStatus('connecting');
          setTimeout(connect, 5000); // Reconnect after 5 seconds
        }
      };

      socket.onerror = (error) => {
        console.error('🔌 WebSocket error:', error);
        setIsConnected(false);
        setIsConnecting(false);
        updateConnectionStatus('disconnected');
        toast.error('Real-time connection error.');
      };
    };

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setIsConnected(false);
      setIsConnecting(false);
      updateConnectionStatus('disconnected');
    };
  }, [isAuthenticated, user?.id, accessToken, handleWebSocketMessage, updateConnectionStatus, options?.onMessage]);

  return {
    isConnected,
    isConnecting,
    refreshDashboard,
  };
}