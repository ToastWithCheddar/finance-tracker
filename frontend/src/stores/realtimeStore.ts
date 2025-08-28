import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { toast } from 'sonner';

import { queryClient, invalidateDashboard, upsertTransactionInCache, removeTransactionFromCache } from '../services/queryClient';
import type { Transaction } from '../types/transaction';
import type { MilestoneAlert } from '../types/goals';
import type { 
  TypedWebSocketMessage, 
  TransactionPayload,
  WebhookSyncPayload,
  TransactionSyncPayload,
  BulkSyncPayload
} from '../types/websocket';
import { 
  MessageType,
  isDashboardUpdate,
  isTransactionMessage,
  isBudgetAlert,
  isGoalProgress,
  isNotification,
  isValidWebSocketMessage,
} from '../types/websocket';

/*****************************
 *  Types & Interfaces
 *****************************/

export interface RealtimeNotification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | string;
  title: string;
  message: string;
  action_url?: string;
  created_at: string; // ISO timestamp string
  read: boolean;
  isNew?: boolean;
}


export interface RealtimeTransaction extends Transaction {
  /** Whether the transaction is newly arrived (for UI highlight) */
  isNew?: boolean;
  /** Whether it is an income (true) or expense (false) */
  is_income: boolean;
  /** Friendly names / extras that might be supplied by the backend */
  category_name?: string;
  category_emoji?: string;
  account_name?: string;
  created_at?: string; // ISO timestamp string – backend may already include this
}

export type ConnectionStatusValue = 'connected' | 'connecting' | 'disconnected';

// Deduplication map for transaction-related WS events (TTL = 60s)
const RECENT_ID_TTL_MS = 60_000;
const recentTransactionIds = new Map<string, number>();
function purgeStaleDedup(now: number) {
  for (const [id, ts] of recentTransactionIds) {
    if (now - ts > RECENT_ID_TTL_MS) recentTransactionIds.delete(id);
  }
}

interface RealtimeState {
  /* WebSocket connection */
  isConnected: boolean;
  connectionStatus: {
    status: ConnectionStatusValue;
    reconnectAttempts: number;
  };

  /* Transactions */
  recentTransactions: RealtimeTransaction[];
  transactionUpdates: Array<{ type: string; transaction?: RealtimeTransaction; transactionId?: string; timestamp?: string }>;

  /* Goals and milestones */
  milestoneAlerts: MilestoneAlert[];
  goalCompletions: Array<{ goal_id: string; goal_name: string }>;
  goalUpdates: Array<{ type: string; data: Record<string, unknown>; timestamp?: string }>;

  /* Notifications */
  notifications: RealtimeNotification[];

  /* Budget alerts */
  budgetAlerts: Array<{ message: string; category?: string; amount?: number }>;




  /* ====== Actions ====== */
  // Connection actions
  updateConnectionStatus: (status: ConnectionStatusValue, reconnectAttempts?: number) => void;

  // Transaction actions
  addRecentTransaction: (transaction: RealtimeTransaction) => void;
  updateTransaction: (transaction: RealtimeTransaction) => void;
  setRecentTransactions: (transactions: RealtimeTransaction[]) => void;
  mergeRecentTransactions: (transactions: RealtimeTransaction[]) => void;
  addTransactionUpdate: (update: { type: string; transaction?: RealtimeTransaction; transactionId?: string }) => void;
  clearTransactionUpdates: () => void;
  markTransactionsSeen: () => void;
  clearOldTransactions: (keepLatest?: number) => void;

  // Goal actions
  addMilestoneAlert: (alert: MilestoneAlert) => void;
  clearMilestoneAlert: (goalId: string) => void;
  addGoalCompletion: (completion: { goal_id: string; goal_name: string }) => void;
  clearGoalCompletion: (goalId: string) => void;
  addGoalUpdate: (update: { type: string; data: Record<string, unknown> }) => void;
  clearGoalUpdates: () => void;

  // Notification actions
  addNotification: (notification: Omit<RealtimeNotification, 'id' | 'created_at' | 'read' | 'isNew'>) => void;
  setNotifications: (items: RealtimeNotification[]) => void;
  mergeNotifications: (items: RealtimeNotification[]) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  dismissNotification: (id: string) => void;
  clearNotifications: () => void;

  // Budget actions
  addBudgetAlert: (alert: { message: string; category?: string; amount?: number }) => void;
  clearBudgetAlerts: () => void;


  // Recurring transaction actions removed

  // Categorization rules removed


  // WebSocket helpers
  handleWebSocketMessage: (message: Record<string, unknown>) => void;
  dispatchMessage: (message: { type: string; payload?: Record<string, unknown>; timestamp?: string }) => void;
}

/*****************************
 *  Store Implementation
 *****************************/

export const useRealtimeStore = create<RealtimeState>()(
  subscribeWithSelector((set, get) => ({
    /***** Initial state *****/
    isConnected: false,
    connectionStatus: {
      status: 'disconnected',
      reconnectAttempts: 0,
    },

    recentTransactions: [],
    transactionUpdates: [],

    milestoneAlerts: [],
    goalCompletions: [],
    goalUpdates: [],

    notifications: [],
    budgetAlerts: [],
    
    
    

    /***** Connection actions *****/
    updateConnectionStatus: (status, reconnectAttempts = 0) => {
      set(() => ({
        isConnected: status === 'connected',
        connectionStatus: {
          status,
          reconnectAttempts,
        },
      }));
    },

    /***** Transaction actions *****/
    addRecentTransaction: (transaction) => {
      set((state) => {
        const byId = new Map(state.recentTransactions.map((t) => [t.id, t] as const));
        // Insert/overwrite with incoming transaction (mark new)
        byId.set(transaction.id, { ...transaction, isNew: true });
        // Sort helper: prefer transactionDate, fallback to created timestamps
        const getTs = (t: any) => {
          const d = (t.transactionDate || t.transaction_date || t.created_at || t.createdAt);
          return d ? new Date(d).getTime() : 0;
        };
        const merged = Array.from(byId.values())
          .sort((a, b) => getTs(b) - getTs(a))
          .slice(0, 50);
        return { recentTransactions: merged };
      });
    },

    updateTransaction: (transaction) => {
      set((state) => {
        const updated = state.recentTransactions.map((t) =>
          t.id === transaction.id ? { ...transaction, isNew: t.isNew } : t,
        );
        const getTs = (t: any) => {
          const d = (t.transactionDate || t.transaction_date || t.created_at || t.createdAt);
          return d ? new Date(d).getTime() : 0;
        };
        updated.sort((a, b) => getTs(b) - getTs(a));
        return { recentTransactions: updated };
      });
    },

    setRecentTransactions: (transactions) => {
      // Replace list, dedup by id, sort by transactionDate desc, ensure isNew=false and max 50 kept
      set(() => {
        const byId = new Map<string, RealtimeTransaction>();
        transactions.forEach((t) => byId.set(t.id, { ...t, isNew: false }));
        const getTs = (t: any) => {
          const d = (t.transactionDate || t.transaction_date || t.created_at || t.createdAt);
          return d ? new Date(d).getTime() : 0;
        };
        const merged = Array.from(byId.values())
          .sort((a, b) => getTs(b) - getTs(a))
          .slice(0, 50);
        return { recentTransactions: merged };
      });
    },

    mergeRecentTransactions: (transactions) => {
      set((state) => {
        const byId = new Map(state.recentTransactions.map((t) => [t.id, t] as const));
        for (const incoming of transactions) {
          const existing = byId.get(incoming.id);
          byId.set(incoming.id, { ...incoming, isNew: existing?.isNew ?? false });
        }
        const getTs = (t: any) => {
          const d = (t.transactionDate || t.transaction_date || t.created_at || t.createdAt);
          return d ? new Date(d).getTime() : 0;
        };
        const merged = Array.from(byId.values())
          .sort((a, b) => getTs(b) - getTs(a))
          .slice(0, 50);
        return { recentTransactions: merged };
      });
    },

    addTransactionUpdate: (update) => {
      set((state) => ({
        transactionUpdates: [
          ...state.transactionUpdates,
          {
            ...update,
            timestamp: new Date().toISOString(),
          },
        ],
      }));
    },

    clearTransactionUpdates: () => {
      set({ transactionUpdates: [] });
    },

    markTransactionsSeen: () => {
      set((state) => ({
        recentTransactions: state.recentTransactions.map((t) => ({ ...t, isNew: false })),
      }));
    },

    clearOldTransactions: (keepLatest = 10) => {
      set((state) => ({
        recentTransactions: state.recentTransactions.slice(0, keepLatest),
      }));
    },

    /***** Goal actions *****/
    addMilestoneAlert: (alert) => {
      set((state) => ({
        milestoneAlerts: [...state.milestoneAlerts, alert],
      }));

      // Also add as notification
      get().addNotification({
        type: 'success',
        title: 'Milestone Achieved!',
        message: alert.celebration_message,
      });
    },

    clearMilestoneAlert: (goalId) => {
      set((state) => ({
        milestoneAlerts: state.milestoneAlerts.filter((alert) => alert.goal_id !== goalId),
      }));
    },

    addGoalCompletion: (completion) => {
      set((state) => ({
        goalCompletions: [...state.goalCompletions, completion],
      }));

      // Celebratory notification
      get().addNotification({
        type: 'success',
        title: 'Goal Completed! 🎊',
        message: `Congratulations on completing "${completion.goal_name}"!`,
      });
    },

    clearGoalCompletion: (goalId) => {
      set((state) => ({
        goalCompletions: state.goalCompletions.filter((comp) => comp.goal_id !== goalId),
      }));
    },

    addGoalUpdate: (update) => {
      set((state) => ({
        goalUpdates: [
          ...state.goalUpdates,
          {
            ...update,
            timestamp: new Date().toISOString(),
          },
        ],
      }));
    },

    clearGoalUpdates: () => {
      set({ goalUpdates: [] });
    },

    /***** Notification actions *****/
    addNotification: (notification) => {
      const newNotification: RealtimeNotification = {
        ...notification,
        id: `notif_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`,
        created_at: new Date().toISOString(),
        read: false,
        isNew: true,
      } as RealtimeNotification;

      set((state) => ({
        notifications: [newNotification, ...state.notifications.slice(0, 49)], // keep max 50
      }));
    },

    setNotifications: (items) => {
      set(() => ({
        notifications: items.slice(0, 50).map((n) => ({ ...n, isNew: false })),
      }));
    },

    mergeNotifications: (items) => {
      set((state) => {
        const byId = new Map(state.notifications.map((n) => [n.id, n] as const));
        for (const incoming of items) {
          const existing = byId.get(incoming.id);
          if (existing) {
            byId.set(incoming.id, {
              ...incoming,
              read: existing.read,
              isNew: false,
            });
          } else {
            byId.set(incoming.id, { ...incoming, isNew: false });
          }
        }
        const merged = Array.from(byId.values())
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 50);
        return { notifications: merged };
      });
    },

    markNotificationRead: (id) => {
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true, isNew: false } : n,
        ),
      }));
    },

    markAllNotificationsRead: () => {
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, read: true, isNew: false })),
      }));
    },

    dismissNotification: (id) => {
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }));
    },

    clearNotifications: () => {
      set({ notifications: [] });
    },

    /***** Budget actions *****/
    addBudgetAlert: (alert) => {
      set((state) => ({
        budgetAlerts: [...state.budgetAlerts, alert],
      }));

      // Also add as notification
      get().addNotification({
        type: 'warning',
        title: 'Budget Alert',
        message: alert.message,
      });
    },

    clearBudgetAlerts: () => {
      set({ budgetAlerts: [] });
    },


    /***** Recurring transaction actions removed *****/

    /***** Categorization rule actions removed *****/


    /***** WebSocket helpers *****/
    handleWebSocketMessage: (message) => {
      try {
        const data = typeof message === 'string' ? JSON.parse(message) : message;

        // Validate message structure
        if (!isValidWebSocketMessage(data)) {
          console.warn('[RealtimeStore] Invalid WebSocket message structure:', data);
          return;
        }

        const typedMessage = data as TypedWebSocketMessage;

        // Handle messages with type safety
        if (isDashboardUpdate(typedMessage)) {
          // Dashboard update - could trigger a full refresh
          console.log('[RealtimeStore] Dashboard update received');
          
        } else if (typedMessage.type === MessageType.BALANCE_UPDATE) {
          const payload = typedMessage.payload as any;
          toast.info(`Balance updated for ${payload.account_name}.`);

          // Invalidate queries that depend on account balances and analytics
          invalidateDashboard();
          queryClient.invalidateQueries({ queryKey: ['accounts'] });
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          
        } else if (isTransactionMessage(typedMessage)) {
          // Dedup guard per-transaction within TTL window
          const now = Date.now();
          purgeStaleDedup(now);
          const payload = typedMessage.payload;
          if (payload?.id) {
            const last = recentTransactionIds.get(payload.id);
            if (last && now - last < RECENT_ID_TTL_MS) {
              console.debug?.('[RealtimeStore] Skipping duplicate NEW_TRANSACTION for id', payload.id);
              return;
            }
            recentTransactionIds.set(payload.id, now);
          }
          const transactionData: RealtimeTransaction = {
            id: payload.id,
            userId: typedMessage.user_id || '',
            accountId: payload.account_id,
            categoryId: payload.category_id,
            amountCents: payload.amount_cents,
            currency: 'USD', // Default currency
            description: payload.description,
            merchant: payload.merchant,
            transactionDate: payload.transaction_date,
            createdAt: payload.created_at || new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            accountName: payload.account_name || 'Unknown Account',
            categoryName: payload.category_name,
            isNew: true,
            is_income: payload.is_income,
            category_name: payload.category_name,
            category_emoji: payload.category_emoji,
            account_name: payload.account_name,
          };
          
          get().addRecentTransaction(transactionData);
          get().addTransactionUpdate({ type: 'created', transaction: transactionData });
          // Apply to any cached list pages where present
          upsertTransactionInCache({
            id: transactionData.id,
            accountId: transactionData.accountId,
            categoryId: transactionData.categoryId,
            amountCents: transactionData.amountCents,
            currency: transactionData.currency,
            description: transactionData.description,
            merchant: transactionData.merchant,
            transactionDate: transactionData.transactionDate,
            createdAt: transactionData.createdAt!,
            updatedAt: transactionData.updatedAt!,
          } as any);
          // Invalidate aggregates and dashboards dependent on transactions
          queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
          invalidateDashboard();
          
        } else if (typedMessage.type === MessageType.TRANSACTION_UPDATED) {
          const now = Date.now();
          purgeStaleDedup(now);
          const payload = typedMessage.payload as TransactionPayload;
          if (payload?.id) {
            const last = recentTransactionIds.get(payload.id);
            if (last && now - last < RECENT_ID_TTL_MS) {
              console.debug?.('[RealtimeStore] Skipping duplicate TRANSACTION_UPDATED for id', payload.id);
              return;
            }
            recentTransactionIds.set(payload.id, now);
          }
          const realtimeTransaction: RealtimeTransaction = {
            id: payload.id,
            userId: typedMessage.user_id || '',
            accountId: payload.account_id,
            categoryId: payload.category_id,
            amountCents: payload.amount_cents,
            currency: 'USD', // Default currency
            description: payload.description,
            merchant: payload.merchant,
            transactionDate: payload.transaction_date,
            createdAt: payload.created_at || new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            accountName: payload.account_name || 'Unknown Account',
            categoryName: payload.category_name,
            isNew: false,
            is_income: payload.is_income,
            category_name: payload.category_name,
            category_emoji: payload.category_emoji,
            account_name: payload.account_name,
          };
          
          get().updateTransaction(realtimeTransaction);
          get().addTransactionUpdate({ type: 'updated', transaction: realtimeTransaction });
          // Apply to any cached list pages where present
          upsertTransactionInCache({
            id: realtimeTransaction.id,
            accountId: realtimeTransaction.accountId,
            categoryId: realtimeTransaction.categoryId,
            amountCents: realtimeTransaction.amountCents,
            currency: realtimeTransaction.currency,
            description: realtimeTransaction.description,
            merchant: realtimeTransaction.merchant,
            transactionDate: realtimeTransaction.transactionDate,
            createdAt: realtimeTransaction.createdAt!,
            updatedAt: realtimeTransaction.updatedAt!,
          } as any);
          // Invalidate aggregates and dashboards dependent on transactions
          queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
          invalidateDashboard();
          
        } else if (typedMessage.type === MessageType.TRANSACTION_DELETED) {
          const now = Date.now();
          purgeStaleDedup(now);
          const payload = typedMessage.payload as { id: string };
          if (payload?.id) {
            const last = recentTransactionIds.get(payload.id);
            if (last && now - last < RECENT_ID_TTL_MS) {
              console.debug?.('[RealtimeStore] Skipping duplicate TRANSACTION_DELETED for id', payload.id);
              return;
            }
            recentTransactionIds.set(payload.id, now);
          }
          set((state) => ({
            recentTransactions: state.recentTransactions.filter((t) => t.id !== payload.id),
          }));
          get().addTransactionUpdate({ type: 'deleted', transactionId: payload.id });
          // Remove from any cached list pages
          removeTransactionFromCache(payload.id);
          // Invalidate aggregates and dashboards dependent on transactions
          queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
          invalidateDashboard();
          
        } else if (typedMessage.type === MessageType.BULK_TRANSACTIONS_IMPORTED) {
          // Handle bulk import notification
          get().addNotification({
            type: 'success',
            title: 'Transactions Imported',
            message: `Successfully imported transactions`,
          });
          // Refresh lists and aggregates after import
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
          invalidateDashboard();
          
        } else if (isBudgetAlert(typedMessage)) {
          get().addBudgetAlert(typedMessage.payload);
          // Budget alerts can change budget state; refresh budgets-related queries
          queryClient.invalidateQueries({ queryKey: ['budgets'] });
          
        } else if (isGoalProgress(typedMessage)) {
          const payload = typedMessage.payload as any;
          get().addGoalUpdate({ type: typedMessage.type, data: payload as Record<string, unknown> });
          
        } else if (typedMessage.type === MessageType.GOAL_ACHIEVED) {
          const payload = typedMessage.payload as { goal_id: string; goal_name: string };
          get().addGoalCompletion(payload);
          
        } else if (typedMessage.type === MessageType.GOAL_MILESTONE_REACHED) {
          const payload = typedMessage.payload as any;
          if (payload && payload.goal_id && payload.goal_name) {
            get().addMilestoneAlert(payload as MilestoneAlert);
          }
          
        } else if (isNotification(typedMessage)) {
          const payload = typedMessage.payload;
          get().addNotification({
            type: payload.notification_type,
            title: payload.title,
            message: payload.message,
            action_url: payload.action_url,
          });
          
        } else if (typedMessage.type === MessageType.WEBHOOK_SYNC_COMPLETE) {
          const payload = typedMessage.payload as WebhookSyncPayload;
          
          if (payload.success && payload.total_new_transactions > 0) {
            toast.success(`Sync complete! ${payload.total_new_transactions} new transaction(s) imported from Plaid.`);
          } else if (payload.success) {
            toast.info('Account sync complete - all transactions are up to date.');
          } else {
            toast.error('Sync failed. Please try again later.');
          }

          // Invalidate queries to trigger refetch
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          queryClient.invalidateQueries({ queryKey: ['accounts'] });
          // Note: dashboard-analytics endpoint no longer exists, invalidating transaction stats instead
          queryClient.invalidateQueries({ queryKey: ['transactions', 'stats'] });
          
        } else if (typedMessage.type === MessageType.TRANSACTION_SYNC_COMPLETE) {
          const payload = typedMessage.payload as TransactionSyncPayload;
          
          if (payload.new_transactions > 0) {
            toast.success(`Sync complete! ${payload.new_transactions} new transaction(s) imported from ${payload.account_name}.`);
          } else {
            toast.info(`${payload.account_name} is up to date.`);
          }

          // Invalidate queries to trigger refetch
          invalidateDashboard();
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          queryClient.invalidateQueries({ queryKey: ['accounts'] });
          queryClient.invalidateQueries({ queryKey: ['budgets'] });
          
        } else if (typedMessage.type === MessageType.BULK_SYNC_COMPLETE) {
          const payload = typedMessage.payload as BulkSyncPayload;
          
          if (payload.total_new_transactions > 0) {
            toast.success(`Bulk sync complete! ${payload.total_new_transactions} new transaction(s) imported.`);
          } else {
            toast.info('Bulk sync complete - all accounts are up to date.');
          }

          if (payload.total_errors > 0) {
            toast.warning(`Sync completed with ${payload.total_errors} error(s). Some accounts may need attention.`);
          }

          // Invalidate queries to trigger refetch
          invalidateDashboard();
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          queryClient.invalidateQueries({ queryKey: ['accounts'] });
          queryClient.invalidateQueries({ queryKey: ['budgets'] });
          
        } else if (typedMessage.type === MessageType.PING) {
          // Handle ping - could send pong response
          console.log('[RealtimeStore] Ping received');
          
        
        } else {
          console.warn('[RealtimeStore] Unhandled WebSocket message type:', typedMessage.type);
        }
      } catch (error) {
        console.error('[RealtimeStore] Error handling WebSocket message:', error, message);
      }
    },

    dispatchMessage: (message) => {
      const transformed = {
        type: message.type,
        data: message.payload,
        timestamp: message.timestamp,
      };
      get().handleWebSocketMessage(transformed);
    },
  }))
);

/*****************************
 *  Selector Hooks
 *****************************/

export const useConnectionStatus = (): RealtimeState['connectionStatus'] =>
  useRealtimeStore((state) => state.connectionStatus);

export const useRealtimeTransactions = () =>
  useRealtimeStore((state) => state.recentTransactions);

export const useNotifications = () =>
  useRealtimeStore((state) => state.notifications);

export const useUnreadNotificationsCount = () =>
  useRealtimeStore((state) => state.notifications.filter((n) => !n.read).length);

export const useBudgetAlerts = () =>
  useRealtimeStore((state) => state.budgetAlerts);

export const useRealtimeStats = () =>
  useRealtimeStore(
    (state) => ({
      transactionCount: state.recentTransactions.length,
      newTransactionCount: state.recentTransactions.filter((t) => t.isNew).length,
      notificationCount: state.notifications.length,
    })
  );

// Rule-related selectors removed


/*****************************
 *  Debug subscriptions (can be removed in prod)
 *****************************/

// Log connection status changes
useRealtimeStore.subscribe(
  (state) => state.connectionStatus,
  (status) => {
    console.log('[RealtimeStore] WebSocket status →', status);
  },
);

// Celebrate new milestones
useRealtimeStore.subscribe(
  (state) => state.milestoneAlerts.length,
  (len, prevLen) => {
    if (len > prevLen) {
    }
  },
);
