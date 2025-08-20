import { useMutation, useQueryClient } from '@tanstack/react-query';
import { transactionService } from '../services/transactionService';
import type { ErrorContext } from '../types/errors';

// Query keys
const MERCHANT_KEYS = {
  all: ['merchants'] as const,
  enrichment: (transactionId: string) => [...MERCHANT_KEYS.all, 'enrichment', transactionId] as const,
  recognition: (description: string) => [...MERCHANT_KEYS.all, 'recognition', description] as const,
  suggestions: (query: string) => [...MERCHANT_KEYS.all, 'suggestions', query] as const,
} as const;

// Hook for merchant enrichment of existing transactions
export function useEnrichTransactionMerchant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ 
      transactionId, 
      description,
      options 
    }: { 
      transactionId: string; 
      description?: string;
      options?: { context?: ErrorContext } 
    }) => {
      return transactionService.enrichTransactionWithMerchant(transactionId, description, options);
    },
    onSuccess: (result, { transactionId }) => {
      // Invalidate transaction queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['transactions', 'detail', transactionId] });
      
      // Cache the enrichment result
      queryClient.setQueryData(
        MERCHANT_KEYS.enrichment(transactionId),
        result
      );
      
      // If the transaction was updated, invalidate related queries
      if (result.updated) {
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        queryClient.invalidateQueries({ queryKey: ['budgets'] });
      }
    },
    meta: {
      onSuccess: (result: any) => {
        console.log('✅ Merchant enrichment successful:', result);
      },
      onError: (error: any) => {
        console.error('❌ Merchant enrichment failed:', error);
      },
    },
  });
}

// Hook for merchant recognition from description (preview mode)
export function useRecognizeMerchantFromDescription() {
  return useMutation({
    mutationFn: async ({ 
      description,
      options 
    }: { 
      description: string;
      options?: { context?: ErrorContext } 
    }) => {
      return transactionService.recognizeMerchantFromDescription(description, options);
    },
    meta: {
      onSuccess: (result: any) => {
        console.log('✅ Merchant recognition successful:', result);
      },
      onError: (error: any) => {
        console.error('❌ Merchant recognition failed:', error);
      },
    },
  });
}

// Hook for getting merchant suggestions (autocomplete)
export function useMerchantSuggestions() {
  return useMutation({
    mutationFn: async ({ 
      query,
      limit = 5,
      options 
    }: { 
      query: string;
      limit?: number;
      options?: { context?: ErrorContext } 
    }) => {
      return transactionService.getMerchantSuggestions(query, limit, options);
    },
    meta: {
      onSuccess: (result: any) => {
        console.log('✅ Merchant suggestions retrieved:', result);
      },
      onError: (error: any) => {
        console.error('❌ Merchant suggestions failed:', error);
      },
    },
  });
}

// Combined hook for all merchant enrichment operations
export function useMerchantActions() {
  const enrichMutation = useEnrichTransactionMerchant();
  const recognizeMutation = useRecognizeMerchantFromDescription();
  const suggestionsMutation = useMerchantSuggestions();

  return {
    // Actions
    enrichTransaction: enrichMutation.mutate,
    recognizeFromDescription: recognizeMutation.mutate,
    getSuggestions: suggestionsMutation.mutate,
    
    // Async versions for better control
    enrichTransactionAsync: enrichMutation.mutateAsync,
    recognizeFromDescriptionAsync: recognizeMutation.mutateAsync,
    getSuggestionsAsync: suggestionsMutation.mutateAsync,
    
    // Loading states
    isEnriching: enrichMutation.isPending,
    isRecognizing: recognizeMutation.isPending,
    isFetchingSuggestions: suggestionsMutation.isPending,
    
    // Results
    enrichmentResult: enrichMutation.data,
    recognitionResult: recognizeMutation.data,
    suggestions: suggestionsMutation.data,
    
    // Errors
    enrichmentError: enrichMutation.error,
    recognitionError: recognizeMutation.error,
    suggestionsError: suggestionsMutation.error,
    
    // Reset functions
    resetEnrichment: enrichMutation.reset,
    resetRecognition: recognizeMutation.reset,
    resetSuggestions: suggestionsMutation.reset,
  };
}

// Hook for live merchant recognition in forms
export function useLiveMerchantRecognition() {
  const recognizeMutation = useRecognizeMerchantFromDescription();
  
  const recognizeFromDescription = async (description: string) => {
    if (!description || description.trim().length < 3) {
      return null;
    }
    
    try {
      const result = await recognizeMutation.mutateAsync({ description });
      return result;
    } catch (error) {
      console.warn('Live merchant recognition failed:', error);
      return null;
    }
  };

  return {
    recognizeFromDescription,
    isRecognizing: recognizeMutation.isPending,
    lastResult: recognizeMutation.data,
    error: recognizeMutation.error,
    reset: recognizeMutation.reset,
  };
}