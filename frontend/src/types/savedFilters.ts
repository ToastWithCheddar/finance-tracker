import type { TransactionFilters } from './transaction';

export interface SavedFilter {
  id: string;
  user_id: string;
  name: string;
  filters: TransactionFilters;
  created_at: string;
  updated_at?: string;
}

export interface SavedFilterCreate {
  name: string;
  filters: TransactionFilters;
  [key: string]: unknown;
}

export interface SavedFilterUpdate {
  name?: string;
  filters?: TransactionFilters;
  [key: string]: unknown;
}