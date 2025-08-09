import { BaseService } from './base/BaseService';
import type { ErrorContext } from '../types/errors';

export interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: string;
  balance_cents: number;
  currency: string;
  is_active: boolean;
  
  // Plaid Integration Fields
  plaid_account_id?: string | null;
  plaid_access_token?: string | null;
  plaid_item_id?: string | null;
  last_sync_at?: string | null;
  
  // Account metadata and sync status
  account_metadata?: Record<string, any> | null;
  sync_status?: string;
  last_sync_error?: string | null;
  
  // Connection health tracking
  connection_health?: string;
  sync_frequency?: string;
  
  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  name: string;
  account_type: string;
  balance_cents?: number;
  currency?: string;
}

export interface AccountUpdate {
  name?: string;
  account_type?: string;
  balance_cents?: number;
  currency?: string;
  is_active?: boolean;
}

export class AccountService extends BaseService {
  protected baseEndpoint = '/accounts';

  async getAccounts(options?: { context?: ErrorContext }): Promise<Account[]> {
    try {
      const response = await this.get<Account[]>(
        this.buildEndpoint(''),
        undefined,
        { context: options?.context }
      );
      
      // Validate response is an array
      if (!Array.isArray(response)) {
        throw new Error('Invalid response format: expected array of accounts');
      }
      
      return response;
    } catch (error: unknown) {
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required to view accounts. Please log in again.');
      }
      
      // Re-throw the original error with context
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to fetch accounts');
    }
  }

  async getAccount(id: string, options?: { context?: ErrorContext }): Promise<Account> {
    try {
      const response = await this.get<Account>(
        this.buildEndpoint(`/${id}`),
        undefined,
        { context: options?.context }
      );
      
      // Validate response structure
      if (!response || !response.id) {
        throw new Error('Invalid account data received');
      }
      
      return response;
    } catch (error: unknown) {
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required to view account. Please log in again.');
      }
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to fetch account');
    }
  }

  async createAccount(
    accountData: AccountCreate,
    options?: { context?: ErrorContext }
  ): Promise<Account> {
    try {
      return await this.post<Account>(
        this.buildEndpoint(''),
        accountData as unknown as Record<string, unknown>,
        { context: options?.context }
      );
    } catch (error: unknown) {
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required to create account. Please log in again.');
      }
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to create account');
    }
  }

  async updateAccount(
    id: string,
    accountData: AccountUpdate,
    options?: { context?: ErrorContext }
  ): Promise<Account> {
    try {
      return await this.put<Account>(
        this.buildEndpoint(`/${id}`),
        accountData as unknown as Record<string, unknown>,
        { context: options?.context }
      );
    } catch (error: unknown) {
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required to update account. Please log in again.');
      }
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to update account');
    }
  }

  async deleteAccount(id: string, options?: { context?: ErrorContext }): Promise<void> {
    try {
      await this.delete(this.buildEndpoint(`/${id}`), { context: options?.context });
    } catch (error: unknown) {
      if ((error as { code?: string })?.code === 'UNAUTHORIZED' || (error as { code?: string })?.code === 'FORBIDDEN') {
        throw new Error('Authentication required to delete account. Please log in again.');
      }
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to delete account');
    }
  }
  
  // Helper methods for account formatting
  formatBalance(balanceCents: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(balanceCents / 100);
  }
  
  getAccountTypeLabel(accountType: string): string {
    const typeLabels: Record<string, string> = {
      'checking': 'Checking',
      'savings': 'Savings',
      'credit_card': 'Credit Card',
      'investment': 'Investment',
      'retirement': 'Retirement',
      'mortgage': 'Mortgage',
      'loan': 'Loan'
    };
    
    return typeLabels[accountType] || accountType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
  
  getConnectionHealthColor(health?: string): string {
    switch (health) {
      case 'healthy': return 'text-green-600';
      case 'warning': return 'text-yellow-600';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-500';
    }
  }
  
  getConnectionHealthLabel(health?: string): string {
    switch (health) {
      case 'healthy': return 'Connected';
      case 'warning': return 'Needs Attention';
      case 'failed': return 'Connection Failed';
      case 'not_connected': return 'Manual Account';
      default: return 'Unknown';
    }
  }
}

export const accountService = new AccountService();