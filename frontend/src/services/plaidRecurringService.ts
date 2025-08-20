import { api } from './api';
import type {
  PlaidRecurringTransaction,
  PlaidRecurringFilter,
  PlaidRecurringSyncResult,
  PlaidRecurringInsights,
  PlaidRecurringStats,
  PlaidRecurringBulkMuteRequest,
  PlaidRecurringBulkMuteResult,
  PlaidRecurringPotentialMatch
} from '../types/plaidRecurring';

export const plaidRecurringService = {
  /**
   * Get user's Plaid recurring transactions with filtering
   */
  getPlaidRecurringTransactions: async (filters?: PlaidRecurringFilter): Promise<PlaidRecurringTransaction[]> => {
    const params = new URLSearchParams();
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, value.toString());
        }
      });
    }
    
    const url = `/recurring/plaid-subscriptions${params.toString() ? `?${params.toString()}` : ''}`;
    return api.get<PlaidRecurringTransaction[]>(url);
  },

  /**
   * Manually sync Plaid recurring transactions for the user
   */
  syncPlaidRecurringTransactions: async (): Promise<PlaidRecurringSyncResult> => {
    return api.post<PlaidRecurringSyncResult>('/recurring/plaid-subscriptions/sync', {});
  },

  /**
   * Get a specific Plaid recurring transaction
   */
  getPlaidRecurringTransaction: async (plaidRecurringId: string): Promise<PlaidRecurringTransaction> => {
    return api.get<PlaidRecurringTransaction>(`/recurring/plaid-subscriptions/${plaidRecurringId}`);
  },

  /**
   * Mute or unmute a Plaid recurring transaction
   */
  mutePlaidRecurringTransaction: async (
    plaidRecurringId: string, 
    muted: boolean
  ): Promise<PlaidRecurringTransaction> => {
    return api.put<PlaidRecurringTransaction>(
      `/recurring/plaid-subscriptions/${plaidRecurringId}/mute?muted=${muted}`,
      {}
    );
  },

  /**
   * Link a Plaid recurring transaction to a recurring transaction rule
   */
  linkPlaidRecurringToRule: async (
    plaidRecurringId: string, 
    ruleId: string
  ): Promise<{ plaid_recurring: PlaidRecurringTransaction; rule: any }> => {
    return api.post<{ plaid_recurring: PlaidRecurringTransaction; rule: any }>(
      `/recurring/plaid-subscriptions/${plaidRecurringId}/link`,
      { rule_id: ruleId }
    );
  },

  /**
   * Unlink a Plaid recurring transaction from its rule
   */
  unlinkPlaidRecurringFromRule: async (plaidRecurringId: string): Promise<PlaidRecurringTransaction> => {
    return api.delete<PlaidRecurringTransaction>(`/recurring/plaid-subscriptions/${plaidRecurringId}/link`);
  },

  /**
   * Find potential rule matches for a Plaid recurring transaction
   */
  findPotentialMatches: async (plaidRecurringId: string): Promise<PlaidRecurringPotentialMatch[]> => {
    return api.get<PlaidRecurringPotentialMatch[]>(
      `/recurring/plaid-subscriptions/${plaidRecurringId}/potential-matches`
    );
  },

  /**
   * Get recurring transaction insights and analytics
   */
  getRecurringInsights: async (): Promise<PlaidRecurringInsights> => {
    return api.get<PlaidRecurringInsights>('/recurring/insights');
  },

  /**
   * Get recurring transaction statistics
   */
  getRecurringStats: async (): Promise<PlaidRecurringStats> => {
    return api.get<PlaidRecurringStats>('/recurring/stats');
  },

  /**
   * Bulk mute/unmute multiple Plaid recurring transactions
   */
  bulkMutePlaidRecurringTransactions: async (
    request: PlaidRecurringBulkMuteRequest
  ): Promise<PlaidRecurringBulkMuteResult> => {
    return api.post<PlaidRecurringBulkMuteResult>(
      `/recurring/plaid-subscriptions/bulk-mute?muted=${request.muted}`,
      { plaid_recurring_ids: request.plaid_recurring_ids }
    );
  },

  /**
   * Export Plaid recurring transactions data
   */
  exportPlaidRecurringTransactions: async (format: 'csv' | 'json' = 'csv'): Promise<Blob> => {
    const response = await fetch(`/api/recurring/plaid-subscriptions/export?format=${format}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Export failed');
    }
    
    return response.blob();
  }
};