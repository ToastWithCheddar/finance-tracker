import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

import type { Transaction } from '../types/transaction';
import type { MilestoneAlert } from '../types/goals';
import type { 
  TypedWebSocketMessage, 
  TransactionPayload
} from '../types/websocket';
import { 
  MessageType,
  isDashboardUpdate,
  isTransactionMessage,
  isBudgetAlert,
  isGoalProgress,
  isNotification,
  isValidWebSocketMessage
} from '../types/websocket';

/*****************************
 *  Types & Interfaces
 *****************************/

export interface RealtimeNotification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | string;
  title: string;
  message: string;
  priority?: 'low' | 'medium' | 'high' | 'critical' | string;
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
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  dismissNotification: (id: string) => void;
  clearNotifications: () => void;

  // Budget actions
  addBudgetAlert: (alert: { message: string; category?: string; amount?: number }) => void;
  clearBudgetAlerts: () => void;

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
      set((state) => ({
        recentTransactions: [
          { ...transaction, isNew: true },
          ...state.recentTransactions.slice(0, 49), // keep max 50
        ],
      }));
    },

    updateTransaction: (transaction) => {
      set((state) => ({
        recentTransactions: state.recentTransactions.map((t) =>
          t.id === transaction.id ? { ...transaction, isNew: t.isNew } : t,
        ),
      }));
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
          
        } else if (isTransactionMessage(typedMessage)) {
          const payload = typedMessage.payload;
          const transactionData: RealtimeTransaction = {
            id: payload.id,
            userId: typedMessage.user_id,
            accountId: payload.account_id,
            categoryId: payload.category_id,
            amountCents: payload.amount_cents,
            currency: 'USD', // Default currency
            description: payload.description,
            merchant: payload.merchant,
            transactionDate: payload.transaction_date,
            isRecurring: false,
            createdAt: payload.created_at || new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            isNew: true,
            is_income: payload.is_income,
            category_name: payload.category_name,
            category_emoji: payload.category_emoji,
            account_name: payload.account_name,
          };
          
          get().addRecentTransaction(transactionData);
          get().addTransactionUpdate({ type: 'created', transaction: transactionData });
          
        } else if (typedMessage.type === MessageType.TRANSACTION_UPDATED) {
          const payload = typedMessage.payload as TransactionPayload;
          const realtimeTransaction: RealtimeTransaction = {
            id: payload.id,
            userId: typedMessage.user_id,
            accountId: payload.account_id,
            categoryId: payload.category_id,
            amountCents: payload.amount_cents,
            currency: 'USD', // Default currency
            description: payload.description,
            merchant: payload.merchant,
            transactionDate: payload.transaction_date,
            isRecurring: false,
            createdAt: payload.created_at || new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            isNew: false,
            is_income: payload.is_income,
            category_name: payload.category_name,
            category_emoji: payload.category_emoji,
            account_name: payload.account_name,
          };
          
          get().updateTransaction(realtimeTransaction);
          get().addTransactionUpdate({ type: 'updated', transaction: realtimeTransaction });
          
        } else if (typedMessage.type === MessageType.TRANSACTION_DELETED) {
          const payload = typedMessage.payload as { id: string };
          set((state) => ({
            recentTransactions: state.recentTransactions.filter((t) => t.id !== payload.id),
          }));
          get().addTransactionUpdate({ type: 'deleted', transactionId: payload.id });
          
        } else if (typedMessage.type === MessageType.BULK_TRANSACTIONS_IMPORTED) {
          // Handle bulk import notification
          get().addNotification({
            type: 'success',
            title: 'Transactions Imported',
            message: `Successfully imported transactions`,
          });
          
        } else if (isBudgetAlert(typedMessage)) {
          get().addBudgetAlert(typedMessage.payload);
          
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
            priority: payload.priority,
            action_url: payload.action_url,
          });
          
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

export const useConnectionStatus = () =>
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
  useRealtimeStore((state) => ({
    transactionCount: state.recentTransactions.length,
    newTransactionCount: state.recentTransactions.filter((t) => t.isNew).length,
    notificationCount: state.notifications.length,
  }));

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
      console.log('[RealtimeStore] 🎉 New milestone achieved!', len);
    }
  },
);
