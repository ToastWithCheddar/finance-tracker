import { BaseService } from './base/BaseService';
import type { SavedFilter, SavedFilterCreate, SavedFilterUpdate } from '../types/savedFilters';

class SavedFilterService extends BaseService {
  protected baseEndpoint = '/saved-filters';

  /**
   * Get all saved filters for the current user
   */
  async getSavedFilters(): Promise<SavedFilter[]> {
    return this.get<SavedFilter[]>('');
  }

  /**
   * Get a specific saved filter by ID
   */
  async getSavedFilter(id: string): Promise<SavedFilter> {
    return this.get<SavedFilter>(`/${id}`);
  }

  /**
   * Create a new saved filter
   */
  async createSavedFilter(savedFilter: SavedFilterCreate): Promise<SavedFilter> {
    return this.post<SavedFilter>('', savedFilter);
  }

  /**
   * Update an existing saved filter
   */
  async updateSavedFilter(id: string, savedFilter: SavedFilterUpdate): Promise<SavedFilter> {
    return this.put<SavedFilter>(`/${id}`, savedFilter);
  }

  /**
   * Delete a saved filter
   */
  async deleteSavedFilter(id: string): Promise<void> {
    return this.delete(`/${id}`);
  }
}

export const savedFilterService = new SavedFilterService();