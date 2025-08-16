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
  force_sync?: boolean;
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
  protected baseEndpoint = '';

  async createLinkToken(
    options?: { context?: ErrorContext }
  ): Promise<PlaidLinkTokenResponse> {
    try {
      const response = await this.post<{ success: boolean; data: PlaidLinkTokenResponse } | PlaidLinkTokenResponse>(
        '/accounts/plaid/link-token',
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
    try {
      // Extract public_token for query parameter, keep metadata for body
      const { public_token, ...bodyData } = exchangeData;
      
      // Build URL with public_token as query parameter
      const baseUrl = this.buildEndpoint('/accounts/plaid/exchange-token');
      const urlWithParams = `${baseUrl}?public_token=${encodeURIComponent(public_token)}`;
      
      console.log('🔗 Exchanging Plaid token...', { url: urlWithParams, hasToken: !!public_token });
      
      const response = await this.post<{ 
        success: boolean; 
        message: string; 
        data: { accounts: PlaidAccount[]; accounts_created: number; institution: string } 
      }>(
        urlWithParams,
        bodyData,
        { context: options?.context }
      );
      
      console.log('✅ Token exchange response:', response);
      
      // Handle both wrapped and direct response formats
      if (response && response.success && response.data) {
        return {
          accounts: response.data.accounts || [],
          message: response.message || `Successfully connected ${response.data.accounts_created} accounts`
        };
      }
      
      // Handle direct format (backwards compatibility)
      if (response && Array.isArray((response as any).accounts)) {
        return {
          accounts: (response as any).accounts,
          message: (response as any).message || 'Accounts connected successfully'
        };
      }
      
      throw new Error('Invalid response format from token exchange endpoint');
      
    } catch (error: unknown) {
      console.error('❌ Token exchange failed:', error);
      
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required for Plaid integration. Please log in again.');
      }
      
      // Extract error message from API response
      const errorMessage = (error as any)?.detail || 
                          (error as any)?.message || 
                          'Failed to connect bank account. Please try again.';
      
      throw new Error(errorMessage);
    }
  }

  async getConnectionStatus(
    options?: { useCache?: boolean; context?: ErrorContext }
  ): Promise<PlaidConnectionStatus> {
    try {
      const response = await this.get<{ success: boolean; data: any } | any>(
        '/accounts/connection-status',
        undefined,
        {
          useCache: options?.useCache ?? true,
          cacheTtl: 30 * 1000,
          context: options?.context
        }
      );
      
      // Normalize payload shape
      const payload = (response && typeof response === 'object' && 'data' in response)
        ? (response as { data: any }).data
        : response;

      if (!payload || typeof payload !== 'object') {
        throw new Error('Invalid response structure from connection status endpoint');
      }

      const totalConnections = (payload.total_connections ?? payload.totalConnections ?? 0) as number;
      const rawAccounts = (payload.accounts ?? []) as Array<any>;

      const normalizedAccounts: PlaidAccount[] = rawAccounts.map((acc: any) => ({
        id: String(acc.id ?? acc.account_id ?? acc.plaid_account_id ?? Math.random()),
        name: acc.name ?? null,
        account_type: acc.account_type ?? acc.type ?? null,
        balance_cents: typeof acc.balance_cents === 'number' ? acc.balance_cents : Math.round((acc.balance ?? 0) * 100),
        currency: acc.currency ?? 'USD',
        plaid_account_id: acc.plaid_account_id ?? acc.account_id ?? null,
        plaid_item_id: acc.plaid_item_id ?? null,
        sync_status: acc.sync_status ?? null,
        connection_health: acc.connection_health ?? acc.health_status ?? null,
        created_at: acc.created_at ?? new Date().toISOString(),
        updated_at: acc.updated_at ?? new Date().toISOString(),
        account_metadata: acc.account_metadata ?? undefined,
      }));

      return {
        success: true,
        connected: totalConnections > 0 || normalizedAccounts.length > 0,
        accounts: normalizedAccounts,
        message: totalConnections > 0 ? 'Connected' : 'Not connected'
      } as PlaidConnectionStatus;
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
    console.log('🔧 PlaidService.syncTransactions called with:', request);
    
    // Prepare request body with proper structure for the backend
    const requestBody: SyncTransactionsRequest = {
      account_ids: request?.account_ids,
      days: request?.days ?? 90  // Default to 90 days for sandbox testing
    };
    
    console.log('📦 Sending transaction sync request body:', requestBody);
    console.log('🎯 Transaction sync endpoint:', this.buildEndpoint('/accounts/sync-transactions'));

    return this.post<SyncTransactionsResponse>(
      '/accounts/sync-transactions',
      requestBody,
      { context: options?.context }
    );
  }

  async syncBalances(
    request?: SyncBalancesRequest,
    options?: { context?: ErrorContext }
  ): Promise<SyncBalancesResponse> {
    console.log('🔧 PlaidService.syncBalances called with:', request);
    
    // Prepare request body with proper structure for the backend
    const requestBody: SyncBalancesRequest = {
      account_ids: request?.account_ids,
      force_sync: request?.force_sync
    };
    
    console.log('📦 Sending request body:', requestBody);
    console.log('🎯 Endpoint:', this.buildEndpoint('/accounts/sync-balances'));

    return this.post<SyncBalancesResponse>(
      '/accounts/sync-balances',
      requestBody,
      { context: options?.context }
    );
  }

  async quickSandboxLink(options?: { context?: ErrorContext }): Promise<{ success: boolean; message: string } | any> {
    return this.post(
      '/accounts/plaid/sandbox/quick-link',
      {},
      { context: options?.context }
    );
  }
}

export const plaidService = new PlaidService();