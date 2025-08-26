import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { useAuthStore } from '../stores/authStore';
import { useRealtimeStore } from '../stores/realtimeStore';
import { transactionService } from '../services/transactionService';
import { NotificationService } from '../services/notificationService';
import { secureStorage } from '../services/secureStorage';

const WEBSOCKET_URL_BASE = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws';

export interface WebSocketMessage {
  type: string;
  payload: any;
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  /** When false, do not establish a WebSocket connection (diagnostics/testing) */
  autoConnect?: boolean;
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
  // Use selectors to avoid re-subscribing to the whole store
  const handleWebSocketMessage = useRealtimeStore(s => s.handleWebSocketMessage);
  const updateConnectionStatus = useRealtimeStore(s => s.updateConnectionStatus);
  const mergeRecentTransactions = useRealtimeStore(s => s.mergeRecentTransactions);
  const mergeNotifications = useRealtimeStore(s => s.mergeNotifications);
  const connectionStatus = useRealtimeStore(s => s.connectionStatus);
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const lastPongRef = useRef<number | null>(null);
  
  // Get token from secure storage
  const accessToken = secureStorage.getAccessToken();
  
  // Store the onMessage callback in a ref to avoid re-creating the effect
  const onMessageRef = useRef(options?.onMessage);
  useEffect(() => {
    const autoConnect = options?.autoConnect ?? true;
    // If disabled, ensure any existing connection is closed and exit
    if (!autoConnect) {
      if (socketRef.current) {
        try { socketRef.current.close(); } catch {}
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
      if (connectionStatus.status !== 'disconnected' || connectionStatus.reconnectAttempts !== 0) {
        updateConnectionStatusRef.current('disconnected', 0);
      }
      return;
    }
    onMessageRef.current = options?.onMessage;
  }, [options?.onMessage]);

  // Store Zustand functions in refs to stabilize effect dependencies
  const handleWebSocketMessageRef = useRef(handleWebSocketMessage);
  const updateConnectionStatusRef = useRef(updateConnectionStatus);
  useEffect(() => {
    handleWebSocketMessageRef.current = handleWebSocketMessage;
  }, [handleWebSocketMessage]);
  useEffect(() => {
    updateConnectionStatusRef.current = updateConnectionStatus;
  }, [updateConnectionStatus]);

  const refreshDashboard = useCallback(() => {
    // Invalidate dashboard queries to trigger a refetch
    // Note: dashboard-analytics endpoint no longer exists, invalidating transaction stats instead
    queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['accounts'] });
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
  }, [queryClient]);

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
      
      // Guard against redundant state updates to prevent loops
      if (connectionStatus.status !== 'disconnected' || connectionStatus.reconnectAttempts !== 0) {
        updateConnectionStatusRef.current('disconnected', 0);
      }
      return;
    }

    // Avoid creating a new connection if one already exists
    if (socketRef.current) {
      return;
    }

    const connect = () => {
      setIsConnecting(true);
      updateConnectionStatusRef.current('connecting', reconnectAttemptsRef.current);
      const socketUrl = `${WEBSOCKET_URL_BASE}?token=${accessToken}`;
      const socket = new WebSocket(socketUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('🔌 WebSocket connection established');
        setIsConnected(true);
        setIsConnecting(false);
        reconnectAttemptsRef.current = 0;
        updateConnectionStatusRef.current('connected', 0);
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

        // Perform light backfill on connect to catch up missed events
        (async () => {
          try {
            const [txs, notifResp] = await Promise.all([
              transactionService.getRecentTransactions(20),
              NotificationService.getNotifications({ limit: 20 }),
            ]);
            const txMapped = txs.map((t: any) => ({
              id: t.id,
              userId: t.userId || t.user_id || '',
              accountId: t.accountId || t.account_id,
              categoryId: t.categoryId || t.category_id,
              amountCents: t.amountCents ?? t.amount_cents ?? 0,
              currency: t.currency || 'USD',
              description: t.description || '',
              merchant: t.merchant,
              transactionDate: (t.transactionDate || t.transaction_date) as string,
              // recurring/subscriptions removed
              createdAt: (t.createdAt || t.created_at || (t.transactionDate ? new Date(t.transactionDate).toISOString() : undefined)) as string,
              updatedAt: (t.updatedAt || t.updated_at || undefined) as string,
              accountName: t.accountName || t.account_name || '',
              categoryName: t.categoryName || t.category_name || undefined,
              isNew: false,
              is_income: (t.amountCents ?? t.amount_cents ?? 0) > 0,
              category_name: t.categoryName || t.category_name,
              account_name: t.accountName || t.account_name,
            }));
            mergeRecentTransactions(txMapped);

            const notifMapped = notifResp.notifications.map((n) => ({
              id: n.id,
              type: n.type,
              title: n.title,
              message: n.message,
              action_url: n.action_url,
              created_at: n.created_at,
              read: n.is_read,
              isNew: false,
            }));
            mergeNotifications(notifMapped);
          } catch (e) {
            console.warn('Realtime backfill failed:', e);
          }
        })();
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
          if (onMessageRef.current) {
            onMessageRef.current(message);
          }

          // Use RealtimeStore's comprehensive message handler
          handleWebSocketMessageRef.current(message);

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
        updateConnectionStatusRef.current('disconnected', reconnectAttemptsRef.current);
        
        // Clear heartbeat timer
        if (heartbeatIntervalRef.current !== null) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }
        
        // Simple reconnect on abnormal close
        if (!event.wasClean) {
          toast.warning('Real-time connection lost. Attempting to reconnect...');
          const nextAttempt = reconnectAttemptsRef.current + 1;
          reconnectAttemptsRef.current = nextAttempt;
          updateConnectionStatusRef.current('connecting', reconnectAttemptsRef.current);
          if (reconnectTimeoutRef.current !== null) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          // Simple 5-second delay instead of exponential backoff
          reconnectTimeoutRef.current = window.setTimeout(() => {
            if (!socketRef.current) {
              connect();
            }
          }, 5000);
        }
      };

      socket.onerror = (error) => {
        console.error('🔌 WebSocket error:', error);
        setIsConnected(false);
        setIsConnecting(false);
        updateConnectionStatusRef.current('disconnected', reconnectAttemptsRef.current);
        toast.error('Real-time connection error.');

        // Clear heartbeat timer
        if (heartbeatIntervalRef.current !== null) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Simple error recovery
        if (socketRef.current) {
          try {
            socketRef.current.close();
          } catch {}
          socketRef.current = null;
        }
        const nextAttempt = reconnectAttemptsRef.current + 1;
        reconnectAttemptsRef.current = nextAttempt;
        updateConnectionStatusRef.current('connecting', reconnectAttemptsRef.current);
        if (reconnectTimeoutRef.current !== null) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        // Simple 5-second delay
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (!socketRef.current) {
            connect();
          }
        }, 5000);
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
      updateConnectionStatusRef.current('disconnected', 0);
    };
  }, [isAuthenticated, user?.id, accessToken, refreshDashboard, options?.autoConnect]);

  return {
    isConnected,
    isConnecting,
    refreshDashboard,
  };
}
