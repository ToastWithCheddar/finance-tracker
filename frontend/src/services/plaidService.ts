import { BaseService } from './base/BaseService';
import type { ErrorContext } from '../types/errors';

export interface PlaidLinkTokenResponse {
  success: boolean;
  link_token: string;
  expiration: string;
  request_id: string;
  environment: string;
}

export interface PlaidExchangeTokenRequest {
  public_token: string;
  metadata: {
    institution: {
      name: string;
      institution_id: string;
    };
    accounts: Array<{
      id: string;
      name: string;
      type: string;
      subtype: string;
    }>;
  };
}

export interface PlaidAccount {
  id: string;
  name: string | null;
  account_type: string | null;
  balance_cents: number | null;
  currency: string;
  plaid_account_id: string;
  plaid_item_id: string;
  sync_status: string | null;
  connection_health: string | null;
  created_at: string;
  updated_at: string;
  account_metadata?: {
    institution_name?: string;
    institution_id?: string;
    institution_url?: string;
    institution_logo?: string;
    institution_primary_color?: string;
    [key: string]: any;
  };
}

export interface PlaidConnectionStatus {
  success: boolean;
  connected: boolean;
  accounts: PlaidAccount[];
  message: string;
}

export interface SyncTransactionsRequest {
  account_ids?: string[];
  days?: number;
  [key: string]: unknown;
}

export interface SyncTransactionsResponse {
  success: boolean;
  message: string;
  data?: {
    results?: Array<{
      account_id: string;
      account_name: string;
      success: boolean;
      new_transactions?: number;
      updated_transactions?: number;
      sync_duration?: number;
      error?: string;
    }>;
    new_transactions?: number;
    updated_transactions?: number;
    sync_duration_seconds?: number;
  };
}

export interface SyncBalancesRequest {
  account_ids?: string[];
  [key: string]: unknown;
}

export interface SyncBalancesResponse {
  success: boolean;
  message: string;
  data?: {
    synced?: Array<{
      account_id: string;
      name: string;
      old_balance: number;
      new_balance: number;
      change: number;
    }>;
    failed?: Array<{
      account_id: string;
      error: string;
    }>;
    total_synced?: number;
    total_failed?: number;
  };
}

export class PlaidService extends BaseService {
  protected baseEndpoint = '/accounts';

  async createLinkToken(
    options?: { context?: ErrorContext }
  ): Promise<PlaidLinkTokenResponse> {
    try {
      const response = await this.post<{ success: boolean; data: PlaidLinkTokenResponse } | PlaidLinkTokenResponse>(
        this.buildEndpoint('/plaid/link-token'),
        {},
        { context: options?.context }
      );
      
      // Handle both wrapped and direct response formats
      if (response && typeof response === 'object') {
        // Check for wrapped format
        if ('data' in response && response.data) {
          return response.data as PlaidLinkTokenResponse;
        }
        // Check for direct format
        if ('link_token' in response && response.link_token) {
          return response as PlaidLinkTokenResponse;
        }
      }
      
      throw new Error('Invalid response structure from link token endpoint');
    } catch (error: unknown) {
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required for Plaid integration. Please log in again.');
      }
      
      // Re-throw the original error with context
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to create Plaid link token');
    }
  }

  async exchangeToken(
    exchangeData: PlaidExchangeTokenRequest,
    options?: { context?: ErrorContext }
  ): Promise<{ accounts: PlaidAccount[]; message: string }> {
    // Extract public_token for query parameter, keep metadata for body
    const { public_token, ...bodyData } = exchangeData;
    
    // Build URL with public_token as query parameter
    const baseUrl = this.buildEndpoint('/plaid/exchange-token');
    const urlWithParams = `${baseUrl}?public_token=${encodeURIComponent(public_token)}`;
    
    return this.post<{ accounts: PlaidAccount[]; message: string }>(
      urlWithParams,
      bodyData,
      { context: options?.context }
    );
  }

  async getConnectionStatus(
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<PlaidConnectionStatus> {
    try {
      const response = await this.get<{ success: boolean; data: PlaidConnectionStatus } | PlaidConnectionStatus>(
        this.buildEndpoint('/connection-status'),
        undefined,
        {
          useCache: options?.useCache ?? true,
          cacheTtl: 30 * 1000,
          context: options?.context
        }
      );
      
      // Handle both wrapped and direct response formats
      if (response && typeof response === 'object') {
        // Check for wrapped format
        if ('data' in response && response.data) {
          return response.data as PlaidConnectionStatus;
        }
        // Check for direct format  
        if ('connected' in response && typeof response.connected === 'boolean') {
          return response as PlaidConnectionStatus;
        }
      }
      
      throw new Error('Invalid response structure from connection status endpoint');
    } catch (error: unknown) {
      const errorObj = error as { code?: string };
      if (errorObj?.code === 'UNAUTHORIZED' || errorObj?.code === 'FORBIDDEN') {
        throw new Error('Authentication required for account status. Please log in again.');
      }
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to get account connection status');
    }
  }

  async syncTransactions(
    request?: SyncTransactionsRequest,
    options?: { context?: ErrorContext }
  ): Promise<SyncTransactionsResponse> {
    // Prepare request body with proper structure for the backend
    const requestBody: SyncTransactionsRequest = {
      account_ids: request?.account_ids,
      days: request?.days ?? 7
    };

    return this.post<SyncTransactionsResponse>(
      this.buildEndpoint('/sync-transactions'),
      requestBody,
      { context: options?.context }
    );
  }

  async syncBalances(
    request?: SyncBalancesRequest,
    options?: { context?: ErrorContext }
  ): Promise<SyncBalancesResponse> {
    // Prepare request body with proper structure for the backend
    const requestBody: SyncBalancesRequest = {
      account_ids: request?.account_ids
    };

    return this.post<SyncBalancesResponse>(
      this.buildEndpoint('/sync-balances'),
      requestBody,
      { context: options?.context }
    );
  }
}

export const plaidService = new PlaidService();