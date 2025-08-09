import { useEffect, useState, useRef, useCallback } from "react";
import { useAuthStore } from "../stores/authStore";
import { useRealtimeStore } from "../stores/realtimeStore";

export interface WebSocketMessage {
    type: string;
    payload: Record<string, unknown>;
    id?: string;
    timestamp: string;
    user_id?: string;
}

export interface WebSocketConfig {
    autoReconnect?: boolean;
    maxRetries?: number;
    reconnectInterval?: number;
    heartbeatInterval?: number;
    debug?: boolean;
    onMessage?: (msg: WebSocketMessage) => void;
}

const DEFAULT_CONFIG: WebSocketConfig = {
    autoReconnect: true,
    maxRetries: 5,
    reconnectInterval: 1000,
    heartbeatInterval: 30000,
    debug: false,
}

// Tracks the connection status and message counts
export interface WebSocketStats {
    isConnected: boolean;
    isConnecting: boolean;
    reConnectAttempts: number;
    lastConnected?: Date;
    lastDisconnected?: Date;
    messagesReceived: number;
    messagesSent: number;
}

export const useWebSocket = (config: WebSocketConfig = {}) => {
    const finalConfig = {...DEFAULT_CONFIG, ...config};
    const { isAuthenticated } = useAuthStore();
    // Get token from secure storage since auth store doesn't store tokens directly
    const getToken = () => {
        try {
            const { secureStorage } = require('../services/secureStorage');
            return secureStorage.getAccessToken() || '';
        } catch {
            return '';
        }
    };
    // If you have useRealtimeStore, uncomment and use it. Otherwise, comment out related usages below.
    const {dispatchMessage, updateConnectionStatus } = useRealtimeStore();
    // const dispatchMessage = () => {};
    // const updateConnectionStatus = () => {};

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const messageQueueRef = useRef<any[]>([]);
    const receivedMessageIds = useRef<Set<string>>(new Set());
    
    const [stats, setStats] = useState<WebSocketStats>({
        isConnected: false,
        isConnecting: false,
        reConnectAttempts: 0,
        messagesReceived: 0,
        messagesSent: 0,
    });

    const wsURL = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/realtime`;

    const log = useCallback((message: string, data?: any) => {
        if (finalConfig.debug) {
            console.log(`[WebSocket] ${message}`, data || '');
        }
    }, [finalConfig.debug]);

    const updateStats = useCallback((updates: Partial<WebSocketStats>) => {
        setStats((prev: WebSocketStats) => ({...prev, ...updates}));
    }, []);

    const clearMessageQueue = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    }, []);

    const clearHeartbeat = useCallback(() => {
        if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
            heartbeatIntervalRef.current = null;
        }
    }, []);

    const sendMessage = useCallback((message: any) => {
        // If the connection is open, send the message
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
                const messageId = {
                    ...message,
                    id: `client_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
                    timestamp: new Date().toISOString()
                };

                wsRef.current.send(JSON.stringify(messageId));
                setStats(prev => ({ ...prev, messagesSent: prev.messagesSent + 1 }));
                log('Message sent', messageId);
                return true;

            } catch (error) {
                log('Failed to send message', error);
                return false;
            } 
        } else {
            // Queue the message if later not connected
            messageQueueRef.current.push(message);
            log('Message queued (not connected)', message);
            return false;
            }
    }, []);

    const sendQueuedMessages = useCallback(() => {
        while (messageQueueRef.current.length > 0) {
            const message = messageQueueRef.current.shift();
            if (!sendMessage(message)) {
                // If sending fails, put it back at the front
                messageQueueRef.current.unshift(message);
                break;
            }
        }
    }, [sendMessage]);

    const startHeartbeat = useCallback(() => {
        clearHeartbeat();
        heartbeatIntervalRef.current = setInterval(() => {
            sendMessage({
                type: "ping",
                payload: {
                    client_time: new Date().toISOString(),
                    sent_at: Date.now()
                }
            });
        }, finalConfig.heartbeatInterval);
    }, [sendMessage, finalConfig.heartbeatInterval, clearHeartbeat]);

    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message : WebSocketMessage = JSON.parse(event.data);

            // Deduplicate messages by id 
            if (message.id && receivedMessageIds.current.has(message.id)) {
                log('Duplicate message received', message)
                return;
            }

            if (message.id) {
                receivedMessageIds.current.add(message.id);
                // Keep only last 1000 messages
                if (receivedMessageIds.current.size > 1000) {
                    const idsArray = Array.from(receivedMessageIds.current);
                    receivedMessageIds.current = new Set(idsArray.slice(-1000));
                }
            }

            setStats(prev => ({ ...prev, messagesReceived: prev.messagesReceived + 1 }));
            log('Message received', message);

            // External callback
            finalConfig.onMessage?.(message);

            // Handle special message types 
            switch (message.type) {
                case "pong":
                    // Calculate the latency if available
                    const sentAt = typeof message.payload.sent_at === 'number' ? message.payload.sent_at : null;
                    const latency = sentAt ? Date.now() - sentAt : null;
                    log('Pong received', {latency});
                    break;
                case "full_sync":
                    // Handle full sync message
                    log('Full sync received');
                    dispatchMessage({type: "full_sync", payload: message.payload, timestamp: new Date().toISOString()});
                    break; 
                case "error":
                    console.error('[WebSocket] Websocket error', message.payload.message);
                    break;

                default:
                    // Dispatch to store
                    dispatchMessage({type: message.type, payload: message.payload, timestamp: new Date().toISOString()});
                    break;
            } 
        }   catch (error) { log('Error parsing message'); }
    }, [dispatchMessage, setStats, log]);

    const connect = useCallback(() => {
        const token = getToken();
        if (!isAuthenticated || !token) {
            log('Not authenticated, skipping connection');
            return;
        }
    
        if (wsRef.current?.readyState === WebSocket.CONNECTING) {
            log('Already connecting, skipping');
            return;
        }
    
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            log('Already connected, skipping');
            return;
        }
    
        try {
            updateStats({
                isConnecting: true,
                reConnectAttempts: reconnectAttemptsRef.current
            });
    
            log('Connecting to WebSocket...', `${wsURL}?token=${token.substring(0, 10)}...`);
    
            wsRef.current = new WebSocket(`${wsURL}?token=${token}`);
    
            wsRef.current.onopen = () => {
                log('WebSocket connected successfully');
                reconnectAttemptsRef.current = 0;
                clearMessageQueue();
    
                updateStats({
                    isConnected: true,
                    isConnecting: false,
                    reConnectAttempts: 0,
                    lastConnected: new Date()
                });
    
                updateConnectionStatus("connected");
                startHeartbeat();
                sendQueuedMessages();
            };
    
            wsRef.current.onmessage = handleMessage;
    
            wsRef.current.onclose = (event) => {
                log('WebSocket disconnected', { code: event.code, reason: event.reason });
    
                updateStats({
                    isConnected: false,
                    isConnecting: false,
                    lastDisconnected: new Date()
                });
    
                updateConnectionStatus("disconnected");
                clearHeartbeat();
    
                // Attempt reconnection if enabled and not a manual close
                if (finalConfig.autoReconnect &&
                    event.code !== 1000 &&
                    reconnectAttemptsRef.current < (finalConfig.maxRetries ?? 5)) {
    
                    const delay = Math.min(
                        finalConfig.reconnectInterval! * Math.pow(2, reconnectAttemptsRef.current),
                        30000
                    );
    
                    reconnectAttemptsRef.current++;
                    log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
    
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, delay);
                } else if (reconnectAttemptsRef.current >= (finalConfig.maxRetries ?? 5)) {
                    log('Max reconnection attempts reached');
                    updateConnectionStatus("disconnected");
                }
            };
    
            wsRef.current.onerror = (error) => {
                log('WebSocket error:', error);
                updateStats({ isConnecting: false });
            };
    
        } catch (error) {
            log('Error creating WebSocket connection:', error);
            updateStats({ isConnecting: false });
        }
    }, [
        isAuthenticated,
        wsURL,
        finalConfig,
        handleMessage,
        updateStats,
        updateConnectionStatus,
        startHeartbeat,
        sendQueuedMessages,
        clearMessageQueue,
        clearHeartbeat,
        log
    ]);
    
    const disconnect = useCallback(() => {
        log('Manually disconnecting...');
        clearMessageQueue();
        clearHeartbeat();
    
        if (wsRef.current) {
            wsRef.current.close(1000, 'Manual disconnect');
            wsRef.current = null;
        }
    
        updateStats({
            isConnected: false,
            isConnecting: false
        });
    
        updateConnectionStatus("disconnected");

    }, [clearMessageQueue, clearHeartbeat, updateStats, updateConnectionStatus, log]);
    
    const reconnect = useCallback(() => {
        log('Manual reconnection requested');
        reconnectAttemptsRef.current = 0;
        disconnect();
        setTimeout(connect, 1000);
    }, [disconnect, connect, log]);
    
    // Subscribe to specific message types
    const subscribe = useCallback((messageTypes: string[]) => {
        sendMessage({
            type: 'subscribe',
            payload: { types: messageTypes }
        });
    }, [sendMessage]);
    
    // Unsubscribe from message types
    const unsubscribe = useCallback((messageTypes: string[]) => {
        sendMessage({
            type: 'unsubscribe',
            payload: { types: messageTypes }
        });
    }, [sendMessage]);
    
    // Request dashboard refresh
    const refreshDashboard = useCallback(() => {
        sendMessage({
            type: 'dashboard_refresh',
            payload: {}
        });
    }, [sendMessage]);
    
    // Mark notifications as read
    const markNotificationsRead = useCallback((notificationIds: string[]) => {
        sendMessage({
            type: 'mark_notification_read',
            payload: { notification_ids: notificationIds }
        });
    }, [sendMessage]);
    
    // Main effect for connection management
    useEffect(() => {
        if (isAuthenticated) {
            connect();
        } else {
            disconnect();
        }
    
        return () => {
            disconnect();
        };
    }, [isAuthenticated, connect, disconnect]);
    
    // Cleanup on unmount
    useEffect(() => {
        return () => {
            clearMessageQueue();
            clearHeartbeat();
            if (wsRef.current) {
                wsRef.current.close(1000, 'Component unmounting');
            }
        };
    }, [clearMessageQueue, clearHeartbeat]);
    
    return {
        // Connection state
        isConnected: stats.isConnected,
        isConnecting: stats.isConnecting,
        stats,
    
        // Actions
        sendMessage,
        disconnect,
        reconnect,
        subscribe,
        unsubscribe,
        refreshDashboard,
        markNotificationsRead,
    
        // Utilities
        log
    };
}    