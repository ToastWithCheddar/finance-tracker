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
  const heartbeatIntervalRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const lastPongRef = useRef<number | null>(null);
  
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
      // Clear timers
      if (heartbeatIntervalRef.current !== null) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current !== null) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      reconnectAttemptsRef.current = 0;
      setIsConnected(false);
      setIsConnecting(false);
      updateConnectionStatus('disconnected', 0);
      return;
    }

    // Avoid creating a new connection if one already exists
    if (socketRef.current) {
      return;
    }

    const connect = () => {
      setIsConnecting(true);
      updateConnectionStatus('connecting', reconnectAttemptsRef.current);
      const socketUrl = `${WEBSOCKET_URL_BASE}?token=${accessToken}`;
      const socket = new WebSocket(socketUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('🔌 WebSocket connection established');
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttemptsRef.current = 0;
        updateConnectionStatus('connected', 0);
        toast.info('Real-time updates connected.');

        // Start heartbeat: send literal 'ping' every 30s
        if (heartbeatIntervalRef.current !== null) {
          clearInterval(heartbeatIntervalRef.current);
        }
        heartbeatIntervalRef.current = window.setInterval(() => {
          if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            try {
              socketRef.current.send('ping');
            } catch (e) {
              console.warn('Heartbeat ping send failed:', e);
            }
          }
        }, 30_000);
      };

      socket.onmessage = (event) => {
        // Heartbeat pong handling
        if (event.data === 'pong') {
          lastPongRef.current = Date.now();
          return;
        }

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
        updateConnectionStatus('disconnected', reconnectAttemptsRef.current);
        
        // Clear heartbeat timer
        if (heartbeatIntervalRef.current !== null) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }
        
        // Exponential backoff reconnect on abnormal close
        if (!event.wasClean) {
          toast.warning('Real-time connection lost. Attempting to reconnect...');
          const nextAttempt = reconnectAttemptsRef.current + 1;
          reconnectAttemptsRef.current = nextAttempt;
          const delay = Math.min(1000 * Math.pow(2, nextAttempt - 1), 30_000);
          updateConnectionStatus('connecting', reconnectAttemptsRef.current);
          if (reconnectTimeoutRef.current !== null) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          reconnectTimeoutRef.current = window.setTimeout(() => {
            if (!socketRef.current) {
              connect();
            }
          }, delay);
        }
      };

      socket.onerror = (error) => {
        console.error('🔌 WebSocket error:', error);
        setIsConnected(false);
        setIsConnecting(false);
        updateConnectionStatus('disconnected', reconnectAttemptsRef.current);
        toast.error('Real-time connection error.');

        // Clear heartbeat timer
        if (heartbeatIntervalRef.current !== null) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Mirror close behavior for reconnection
        if (socketRef.current) {
          try {
            socketRef.current.close();
          } catch {}
          socketRef.current = null;
        }
        const nextAttempt = reconnectAttemptsRef.current + 1;
        reconnectAttemptsRef.current = nextAttempt;
        const delay = Math.min(1000 * Math.pow(2, nextAttempt - 1), 30_000);
        updateConnectionStatus('connecting', reconnectAttemptsRef.current);
        if (reconnectTimeoutRef.current !== null) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (!socketRef.current) {
            connect();
          }
        }, delay);
      };
    };

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      if (heartbeatIntervalRef.current !== null) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current !== null) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      reconnectAttemptsRef.current = 0;
      setIsConnected(false);
      setIsConnecting(false);
      updateConnectionStatus('disconnected', 0);
    };
  }, [isAuthenticated, user?.id, accessToken, handleWebSocketMessage, updateConnectionStatus, options?.onMessage]);

  return {
    isConnected,
    isConnecting,
    refreshDashboard,
  };
}
