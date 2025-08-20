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
  
  // Webhook sync events
  WEBHOOK_SYNC_COMPLETE: 'webhook_sync_complete',
  TRANSACTION_SYNC_COMPLETE: 'transaction_sync_complete',
  BULK_SYNC_COMPLETE: 'bulk_sync_complete',
  
  // Plaid recurring transactions
  PLAID_RECURRING_SYNCED: 'plaid_recurring_synced',
  PLAID_RECURRING_UPDATED: 'plaid_recurring_updated',
  RECURRING_TRANSACTION_MUTED: 'recurring_transaction_muted',
  RECURRING_TRANSACTION_LINKED: 'recurring_transaction_linked',
  
  // Categorization rules
  CATEGORIZATION_RULE_CREATED: 'categorization_rule_created',
  CATEGORIZATION_RULE_UPDATED: 'categorization_rule_updated',
  CATEGORIZATION_RULE_DELETED: 'categorization_rule_deleted',
  CATEGORIZATION_RULE_APPLIED: 'categorization_rule_applied',
  RULE_EFFECTIVENESS_UPDATED: 'rule_effectiveness_updated',
  
  // User activity events
  USER_ACTIVITY_CREATED: 'user_activity_created',
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
  id?: string;
  type: MessageType;
  timestamp?: string; // ISO datetime string
  user_id?: string;
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

export interface WebhookSyncPayload {
  item_id: string;
  total_new_transactions: number;
  total_updated_transactions: number;
  accounts_synced: number;
  sync_time: string; // ISO datetime string
  success: boolean;
}

export interface TransactionSyncPayload {
  account_id: string;
  account_name: string;
  new_transactions: number;
  updated_transactions: number;
  duplicates_skipped: number;
  sync_duration: number;
  date_range: string;
}

export interface BulkSyncPayload {
  total_new_transactions: number;
  total_updated_transactions: number;
  total_errors: number;
  sync_time: string; // ISO datetime string
}

export interface PlaidRecurringSyncPayload {
  account_id: string;
  account_name: string;
  recurring_transactions_count: number;
  new_subscriptions: number;
  updated_subscriptions: number;
  synced_at: string; // ISO datetime string
}

export interface PlaidRecurringUpdatePayload {
  stream_id: string;
  account_id: string;
  merchant_name: string;
  description: string;
  amount_cents: number;
  frequency: string;
  status: 'active' | 'inactive' | 'muted';
  is_active: boolean;
  confidence: number;
  updated_at: string; // ISO datetime string
}

export interface RecurringTransactionActionPayload {
  stream_id: string;
  account_id: string;
  merchant_name: string;
  action: 'muted' | 'unmuted' | 'linked' | 'unlinked';
  transaction_id?: string; // for linking actions
  performed_at: string; // ISO datetime string
}

export interface CategorizationRuleActionPayload {
  rule_id: string;
  rule_name: string;
  action: 'created' | 'updated' | 'deleted' | 'activated' | 'deactivated';
  priority?: number;
  conditions?: Record<string, any>;
  actions?: Record<string, any>;
  performed_at: string; // ISO datetime string
}

export interface RuleApplicationPayload {
  rule_id: string;
  rule_name: string;
  transaction_id: string;
  transaction_description: string;
  old_category_id?: string;
  new_category_id: string;
  confidence_score: number;
  applied_at: string; // ISO datetime string
}

export interface RuleEffectivenessPayload {
  rule_id: string;
  rule_name: string;
  times_applied: number;
  success_rate: number;
  avg_confidence_score: number;
  total_transactions_affected: number;
  last_applied_at?: string; // ISO datetime string
  updated_at: string; // ISO datetime string
}

export interface UserActivityPayload {
  id: string;
  type: string;
  title: string;
  description: string;
  table_name?: string;
  record_id?: string;
  metadata?: Record<string, any>;
  created_at: string; // ISO datetime string
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
  | BatchUpdatePayload
  | WebhookSyncPayload
  | TransactionSyncPayload
  | BulkSyncPayload
  | PlaidRecurringSyncPayload
  | PlaidRecurringUpdatePayload
  | RecurringTransactionActionPayload
  | CategorizationRuleActionPayload
  | RuleApplicationPayload
  | RuleEffectivenessPayload
  | UserActivityPayload;

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

export function isPlaidRecurringSync(message: WebSocketMessage): boolean {
  return message.type === MessageType.PLAID_RECURRING_SYNCED;
}

export function isPlaidRecurringUpdate(message: WebSocketMessage): boolean {
  return message.type === MessageType.PLAID_RECURRING_UPDATED;
}

export function isRecurringTransactionAction(message: WebSocketMessage): boolean {
  return message.type === MessageType.RECURRING_TRANSACTION_MUTED || 
         message.type === MessageType.RECURRING_TRANSACTION_LINKED;
}

export function isCategorizationRuleAction(message: WebSocketMessage): boolean {
  return message.type === MessageType.CATEGORIZATION_RULE_CREATED ||
         message.type === MessageType.CATEGORIZATION_RULE_UPDATED ||
         message.type === MessageType.CATEGORIZATION_RULE_DELETED;
}

export function isRuleApplication(message: WebSocketMessage): boolean {
  return message.type === MessageType.CATEGORIZATION_RULE_APPLIED;
}

export function isRuleEffectivenessUpdate(message: WebSocketMessage): boolean {
  return message.type === MessageType.RULE_EFFECTIVENESS_UPDATED;
}

export function isUserActivity(message: WebSocketMessage): boolean {
  return message.type === MessageType.USER_ACTIVITY_CREATED;
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
    typeof (data as any).type === 'string' &&
    (data as any).payload &&
    typeof (data as any).payload === 'object'
  );
}

export function validateMessageType(type: string): type is MessageType {
  return Object.values(MessageType).includes(type as MessageType);
}