import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { savedFilterService } from '../services/savedFilterService';
import type { SavedFilter, SavedFilterCreate, SavedFilterUpdate } from '../types/savedFilters';

// Query keys
const QUERY_KEYS = {
  savedFilters: ['saved-filters'] as const,
  savedFilter: (id: string) => ['saved-filters', id] as const,
};

/**
 * Hook to fetch all saved filters
 */
export function useSavedFilters() {
  return useQuery({
    queryKey: QUERY_KEYS.savedFilters,
    queryFn: () => savedFilterService.getSavedFilters(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch a specific saved filter
 */
export function useSavedFilter(id: string) {
  return useQuery({
    queryKey: QUERY_KEYS.savedFilter(id),
    queryFn: () => savedFilterService.getSavedFilter(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create a new saved filter
 */
export function useCreateSavedFilter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SavedFilterCreate) => savedFilterService.createSavedFilter(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.savedFilters });
      toast.success('Filter saved successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to save filter');
    },
  });
}

/**
 * Hook to update a saved filter
 */
export function useUpdateSavedFilter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SavedFilterUpdate }) =>
      savedFilterService.updateSavedFilter(id, data),
    onSuccess: (updatedFilter) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.savedFilters });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.savedFilter(updatedFilter.id) });
      toast.success('Filter updated successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to update filter');
    },
  });
}

/**
 * Hook to delete a saved filter
 */
export function useDeleteSavedFilter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => savedFilterService.deleteSavedFilter(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.savedFilters });
      toast.success('Filter deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to delete filter');
    },
  });
}

/**
 * Utility hook for saved filter operations
 */
export function useSavedFilterOperations() {
  const createMutation = useCreateSavedFilter();
  const updateMutation = useUpdateSavedFilter();
  const deleteMutation = useDeleteSavedFilter();

  return {
    create: createMutation.mutate,
    update: updateMutation.mutate,
    delete: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isLoading: createMutation.isPending || updateMutation.isPending || deleteMutation.isPending,
  };
}