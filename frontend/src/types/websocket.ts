/**
 * Type-safe WebSocket message definitions for real-time communication
 * These types should match the backend schemas in backend/app/websocket/schemas.py
 */

// Message Types Enum
export const MessageType = {
  // Dashboard updates
  DASHBOARD_UPDATE: 'dashboard_update',
  BALANCE_UPDATE: 'balance_update',
  NET_WORTH_UPDATE: 'net_worth_update',
  
  // Transaction events
  NEW_TRANSACTION: 'new_transaction',
  TRANSACTION_UPDATED: 'transaction_updated',
  TRANSACTION_DELETED: 'transaction_deleted',
  BULK_TRANSACTIONS_IMPORTED: 'bulk_transactions_imported',
  
  // Account events
  ACCOUNT_CREATED: 'account_created',
  ACCOUNT_UPDATED: 'account_updated',
  ACCOUNT_SYNCED: 'account_synced',
  ACCOUNT_SYNC_ERROR: 'account_sync_error',
  
  // Budget events
  BUDGET_ALERT: 'budget_alert',
  BUDGET_THRESHOLD_REACHED: 'budget_threshold_reached',
  BUDGET_EXCEEDED: 'budget_exceeded',
  MONTHLY_BUDGET_RESET: 'monthly_budget_reset',
  
  // Goal events
  GOAL_PROGRESS_UPDATE: 'goal_progress_update',
  GOAL_ACHIEVED: 'goal_achieved',
  GOAL_MILESTONE_REACHED: 'goal_milestone_reached',
  
  // Insights and AI
  AI_INSIGHT_GENERATED: 'ai_insight_generated',
  SPENDING_PATTERN_DETECTED: 'spending_pattern_detected',
  CATEGORY_SUGGESTION: 'category_suggestion',
  
  // System events
  NOTIFICATION: 'notification',
  SYSTEM_ALERT: 'system_alert',
  FULL_SYNC: 'full_sync',
  PING: 'ping',
  PONG: 'pong',
  BATCH_UPDATE: 'batch_update',
} as const;

export type MessageType = typeof MessageType[keyof typeof MessageType];

export const NotificationPriority = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;

export type NotificationPriority = typeof NotificationPriority[keyof typeof NotificationPriority];

// Base WebSocket Message
export interface WebSocketMessage {
  id: string;
  type: MessageType;
  timestamp: string; // ISO datetime string
  user_id: string;
}

// Payload interfaces for different message types

export interface DashboardUpdatePayload {
  total_balance?: number; // in cents
  monthly_spending?: number; // in cents
  monthly_income?: number; // in cents
  budget_utilization?: number; // percentage
  active_goals?: number;
  recent_transactions: TransactionPayload[];
  account_summary?: {
    account_id: string;
    account_name: string;
    account_type: string;
    balance_cents: number;
    currency: string;
  }[];
  spending_by_category: {
    category_id: string;
    category_name: string;
    category_emoji?: string;
    amount_cents: number;
    transaction_count: number;
    percentage: number;
  }[];
  updated_at: string; // ISO datetime string
}

export interface BalanceUpdatePayload {
  account_id: string;
  account_name: string;
  old_balance_cents: number;
  new_balance_cents: number;
  change_cents: number;
  updated_at: string; // ISO datetime string
}

export interface TransactionPayload {
  id: string;
  amount_cents: number;
  description: string;
  merchant?: string;
  category_id?: string;
  category_name?: string;
  category_emoji?: string;
  account_id: string;
  account_name?: string;
  transaction_date: string; // ISO date string
  created_at?: string; // ISO datetime string
  is_income: boolean;
}

export interface BulkTransactionImportPayload {
  account_id: string;
  account_name: string;
  transaction_count: number;
  imported_at: string; // ISO datetime string
}

export interface BudgetAlertPayload {
  budget_id: string;
  budget_name: string;
  category_name?: string;
  amount_cents: number;
  spent_cents: number;
  remaining_cents: number;
  percentage_used: number;
  alert_type: string;
  priority: NotificationPriority;
  message: string;
  period: string;
  threshold_reached: boolean;
}

export interface GoalProgressPayload {
  goal_id: string;
  goal_name: string;
  target_amount_cents: number;
  current_amount_cents: number;
  remaining_cents: number;
  progress_percentage: number;
  target_date?: string; // ISO date string
  is_achieved: boolean;
  milestone_reached: boolean;
}

export interface GoalAchievedPayload {
  goal_id: string;
  goal_name: string;
  target_amount_cents: number;
  achieved_amount_cents: number;
  achievement_date: string; // ISO datetime string
  celebration_message: string;
  priority: NotificationPriority;
}

export interface AccountSyncPayload {
  account_id: string;
  account_name?: string;
  transactions_added: number;
  balance_updated: boolean;
  new_balance_cents?: number;
  sync_duration_ms?: number;
  synced_at: string; // ISO datetime string
  success: boolean;
}

export interface AccountSyncErrorPayload {
  account_id: string;
  account_name?: string;
  error_message: string;
  error_code?: string;
  retry_suggested: boolean;
  failed_at: string; // ISO datetime string
  priority: NotificationPriority;
}

export interface NotificationPayload {
  id: string;
  title: string;
  message: string;
  notification_type: 'success' | 'error' | 'warning' | 'info';
  priority: NotificationPriority;
  action_url?: string;
  metadata: Record<string, unknown>;
  created_at: string; // ISO datetime string
  read: boolean;
}

export interface SystemAlertPayload {
  alert_type: string;
  message: string;
  priority: NotificationPriority;
  system_wide: boolean;
  created_at: string; // ISO datetime string
}

export interface AIInsightPayload {
  insight_id: string;
  title: string;
  description: string;
  insight_type: string;
  data: Record<string, unknown>;
  confidence_score?: number;
  actionable: boolean;
  action_items: string[];
  priority: NotificationPriority;
  generated_at: string; // ISO datetime string
}

export interface PingPayload {
  server_time: string; // ISO datetime string
  connection_status: 'active' | 'idle';
}

export interface BatchUpdatePayload {
  events: TypedWebSocketMessage[];
  count: number;
  batch_id: string;
}

// Union type for all possible payloads
export type PayloadType = 
  | DashboardUpdatePayload
  | BalanceUpdatePayload
  | TransactionPayload
  | BulkTransactionImportPayload
  | BudgetAlertPayload
  | GoalProgressPayload
  | GoalAchievedPayload
  | AccountSyncPayload
  | AccountSyncErrorPayload
  | NotificationPayload
  | SystemAlertPayload
  | AIInsightPayload
  | PingPayload
  | BatchUpdatePayload;

// Typed WebSocket Messages
export interface TypedWebSocketMessage extends WebSocketMessage {
  payload: PayloadType;
}

// Specific message types for better type inference
export interface DashboardUpdateMessage extends WebSocketMessage {
  type: typeof MessageType.DASHBOARD_UPDATE;
  payload: DashboardUpdatePayload;
}

export interface TransactionMessage extends WebSocketMessage {
  type: typeof MessageType.NEW_TRANSACTION;
  payload: TransactionPayload;
}

export interface BudgetAlertMessage extends WebSocketMessage {
  type: typeof MessageType.BUDGET_ALERT;
  payload: BudgetAlertPayload;
}

export interface GoalProgressMessage extends WebSocketMessage {
  type: typeof MessageType.GOAL_PROGRESS_UPDATE;
  payload: GoalProgressPayload;
}

export interface NotificationMessage extends WebSocketMessage {
  type: typeof MessageType.NOTIFICATION;
  payload: NotificationPayload;
}

// Message type guards for runtime type checking
export function isDashboardUpdate(message: WebSocketMessage): message is DashboardUpdateMessage {
  return message.type === MessageType.DASHBOARD_UPDATE;
}

export function isTransactionMessage(message: WebSocketMessage): message is TransactionMessage {
  return message.type === MessageType.NEW_TRANSACTION;
}

export function isBudgetAlert(message: WebSocketMessage): message is BudgetAlertMessage {
  return message.type === MessageType.BUDGET_ALERT;
}

export function isGoalProgress(message: WebSocketMessage): message is GoalProgressMessage {
  return message.type === MessageType.GOAL_PROGRESS_UPDATE;
}

export function isNotification(message: WebSocketMessage): message is NotificationMessage {
  return message.type === MessageType.NOTIFICATION;
}

// WebSocket connection status
export const ConnectionStatus = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  FAILED: 'failed',
} as const;

export type ConnectionStatus = typeof ConnectionStatus[keyof typeof ConnectionStatus];

export interface WebSocketConnectionState {
  status: ConnectionStatus;
  lastConnected?: Date;
  lastDisconnected?: Date;
  reconnectAttempts: number;
  error?: string;
}

// Helper functions for message validation
export function isValidWebSocketMessage(data: unknown): data is TypedWebSocketMessage {
  return (
    data &&
    typeof data === 'object' &&
    data !== null &&
    typeof (data as any).id === 'string' &&
    typeof (data as any).type === 'string' &&
    typeof (data as any).timestamp === 'string' &&
    typeof (data as any).user_id === 'string' &&
    (data as any).payload &&
    typeof (data as any).payload === 'object'
  );
}

export function validateMessageType(type: string): type is MessageType {
  return Object.values(MessageType).includes(type as MessageType);
}