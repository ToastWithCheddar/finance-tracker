import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { categoryService } from '../services/categoryService';
import type { Category, CreateCategoryRequest, UpdateCategoryRequest } from '../types/category';

const CATEGORIES_QUERY_KEY = ['categories'];

// Hook to fetch all categories (system + user's custom categories)
export function useCategories() {
  return useQuery({
    queryKey: CATEGORIES_QUERY_KEY,
    queryFn: () => categoryService.getMyCategories(true), // Include system categories
    staleTime: 5 * 60 * 1000, // Consider categories fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Cache for 10 minutes
  });
}

// Hook to fetch system categories only
export function useSystemCategories() {
  return useQuery({
    queryKey: [...CATEGORIES_QUERY_KEY, 'system'],
    queryFn: () => categoryService.getSystemCategories(),
    staleTime: 30 * 60 * 1000, // System categories rarely change
    gcTime: 60 * 60 * 1000, // Cache for 1 hour
  });
}

// Hook to fetch categories for a specific transaction type
export function useCategoriesForTransactionType(type?: 'income' | 'expense') {
  return useQuery({
    queryKey: [...CATEGORIES_QUERY_KEY, 'transaction-type', type],
    queryFn: () => {
      if (!type) return categoryService.getMyCategories(true);
      return categoryService.getCategoriesForTransactionType(type);
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled: !!type, // Only fetch when type is provided
  });
}

// Hook for category mutations
export function useCategoryActions() {
  const queryClient = useQueryClient();

  const createCategory = useMutation({
    mutationFn: (data: CreateCategoryRequest) => categoryService.createCategory(data),
    onSuccess: () => {
      // Invalidate all category queries
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });

  const updateCategory = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCategoryRequest }) => 
      categoryService.updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });

  const deleteCategory = useMutation({
    mutationFn: (id: string) => categoryService.deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });

  return {
    createCategory,
    updateCategory,
    deleteCategory,
    isCreating: createCategory.isPending,
    isUpdating: updateCategory.isPending,
    isDeleting: deleteCategory.isPending,
  };
}

// Hook to find a category by ID (useful for resolving category names)
export function useCategory(categoryId?: string) {
  return useQuery({
    queryKey: [...CATEGORIES_QUERY_KEY, 'single', categoryId],
    queryFn: () => categoryService.getCategory(categoryId!),
    enabled: !!categoryId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

// Helper hook to get a map of category ID to category object
export function useCategoryMap() {
  const { data: categories = [], ...rest } = useCategories();
  
  const categoryMap = categories.reduce((map, category) => {
    map.set(category.id, category);
    return map;
  }, new Map<string, Category>());

  return {
    categoryMap,
    categories,
    ...rest
  };
}

// Helper hook to get category name by ID
export function useCategoryName(categoryId?: string) {
  const { categoryMap } = useCategoryMap();
  
  if (!categoryId) return undefined;
  
  const category = categoryMap.get(categoryId);
  return category?.name;
}