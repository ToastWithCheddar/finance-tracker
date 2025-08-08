import { apiClient } from './api';
import type { 
  Category, 
  CreateCategoryRequest, 
  UpdateCategoryRequest, 
  CategoryWithChildren,
  CategoryStats 
} from '../types/category';

export class CategoryService {
  private baseEndpoint = '/categories';

  /**
   * Get all categories (system + user's custom categories)
   */
  async getCategories(params?: {
    skip?: number;
    limit?: number;
    include_system?: boolean;
    parent_only?: boolean;
    search?: string;
  }): Promise<Category[]> {
    return apiClient.get<Category[]>(this.baseEndpoint, params);
  }

  /**
   * Get all system (default) categories
   */
  async getSystemCategories(): Promise<Category[]> {
    return apiClient.get<Category[]>(`${this.baseEndpoint}/system`);
  }

  /**
   * Get current user's categories (custom + system)
   */
  async getMyCategories(includeSystem: boolean = true): Promise<Category[]> {
    return apiClient.get<Category[]>(`${this.baseEndpoint}/my`, {
      include_system: includeSystem
    });
  }

  /**
   * Get a specific category by ID
   */
  async getCategory(id: string): Promise<Category> {
    return apiClient.get<Category>(`${this.baseEndpoint}/${id}`);
  }

  /**
   * Create a new custom category
   */
  async createCategory(categoryData: CreateCategoryRequest): Promise<Category> {
    return apiClient.post<Category>(this.baseEndpoint, categoryData);
  }

  /**
   * Update a custom category
   */
  async updateCategory(id: string, categoryData: UpdateCategoryRequest): Promise<Category> {
    return apiClient.put<Category>(`${this.baseEndpoint}/${id}`, categoryData);
  }

  /**
   * Delete a custom category
   */
  async deleteCategory(id: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`${this.baseEndpoint}/${id}`);
  }

  /**
   * Get categories organized in hierarchical structure
   */
  async getCategoriesHierarchy(params?: {
    include_system?: boolean;
  }): Promise<CategoryWithChildren[]> {
    // Use the new hierarchy endpoint for better performance
    return apiClient.get<CategoryWithChildren[]>(`${this.baseEndpoint}/hierarchy`, params);
  }

  /**
   * Get category statistics
   */
  async getCategoryStats(_categoryId: string): Promise<CategoryStats> {
    void _categoryId; // param currently unused
    // This would need to be implemented on the backend
    // For now, return mock data
    return {
      transaction_count: 0,
      total_amount_cents: 0
    };
  }

  /**
   * Search categories by name
   */
  async searchCategories(query: string, includeSystem: boolean = true): Promise<Category[]> {
    return this.getCategories({
      search: query,
      include_system: includeSystem,
      limit: 50
    });
  }

  /**
   * Get categories suitable for a specific transaction type
   */
  async getCategoriesForTransactionType(type: 'income' | 'expense'): Promise<Category[]> {
    const categories = await this.getMyCategories();
    
    // Filter categories based on common usage patterns
    if (type === 'income') {
      return categories.filter(cat => 
        cat.name.toLowerCase().includes('income') ||
        cat.name.toLowerCase().includes('salary') ||
        cat.name.toLowerCase().includes('freelance') ||
        cat.name.toLowerCase().includes('business') ||
        cat.name.toLowerCase().includes('investment') ||
        cat.name.toLowerCase().includes('bonus') ||
        cat.name.toLowerCase().includes('refund')
      );
    }
    
    // For expenses, return all non-income categories
    return categories.filter(cat => 
      !cat.name.toLowerCase().includes('income') &&
      !cat.name.toLowerCase().includes('salary') &&
      !cat.name.toLowerCase().includes('freelance') &&
      !cat.name.toLowerCase().includes('investment')
    );
  }
}

// Create and export a singleton instance
export const categoryService = new CategoryService();