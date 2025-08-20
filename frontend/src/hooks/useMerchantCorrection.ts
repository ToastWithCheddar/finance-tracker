import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { transactionService } from '../services/transactionService';
import type { ErrorContext } from '../types/errors';

// Interface for correction state management
interface MerchantCorrectionState {
  isCorrectingMerchant: boolean;
  merchantCorrection: string;
  isSavingCorrection: boolean;
  correctionError: string | null;
}

// Hook for correcting merchant information
export function useCorrectTransactionMerchant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ 
      transactionId, 
      merchantName,
      options 
    }: { 
      transactionId: string; 
      merchantName: string;
      options?: { context?: ErrorContext } 
    }) => {
      return transactionService.correctTransactionMerchant(transactionId, merchantName, options);
    },
    onSuccess: (result, { transactionId }) => {
      // Invalidate transaction queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['transactions', 'detail', transactionId] });
      
      // If the learning system was updated, invalidate merchant queries
      if (result.learning_updated) {
        queryClient.invalidateQueries({ queryKey: ['merchants'] });
      }
      
      // Invalidate related queries that might be affected
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    meta: {
      onSuccess: (result: any) => {
        console.log('✅ Merchant correction successful:', result);
      },
      onError: (error: any) => {
        console.error('❌ Merchant correction failed:', error);
      },
    },
  });
}

// Comprehensive hook for managing merchant correction state and actions
export function useMerchantCorrectionManager(initialMerchant: string = '') {
  const [state, setState] = useState<MerchantCorrectionState>({
    isCorrectingMerchant: false,
    merchantCorrection: initialMerchant,
    isSavingCorrection: false,
    correctionError: null,
  });

  const correctMutation = useCorrectTransactionMerchant();

  const startCorrection = (currentMerchant: string = '') => {
    setState(prev => ({
      ...prev,
      isCorrectingMerchant: true,
      merchantCorrection: currentMerchant,
      correctionError: null,
    }));
  };

  const cancelCorrection = () => {
    setState(prev => ({
      ...prev,
      isCorrectingMerchant: false,
      merchantCorrection: initialMerchant,
      correctionError: null,
    }));
    correctMutation.reset();
  };

  const updateCorrection = (value: string) => {
    setState(prev => ({
      ...prev,
      merchantCorrection: value,
      correctionError: null,
    }));
  };

  const saveCorrection = async (transactionId: string) => {
    if (!state.merchantCorrection.trim()) {
      setState(prev => ({
        ...prev,
        correctionError: 'Merchant name cannot be empty',
      }));
      return false;
    }

    setState(prev => ({ ...prev, isSavingCorrection: true }));

    try {
      await correctMutation.mutateAsync({
        transactionId,
        merchantName: state.merchantCorrection.trim(),
      });

      setState(prev => ({
        ...prev,
        isCorrectingMerchant: false,
        isSavingCorrection: false,
        correctionError: null,
      }));

      return true;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isSavingCorrection: false,
        correctionError: error instanceof Error ? error.message : 'Failed to save correction',
      }));
      return false;
    }
  };

  return {
    // State
    ...state,
    
    // Actions
    startCorrection,
    cancelCorrection,
    updateCorrection,
    saveCorrection,
    
    // Mutation data
    correctionResult: correctMutation.data,
    
    // Computed states
    canSave: state.merchantCorrection.trim().length > 0 && !state.isSavingCorrection,
    hasUnsavedChanges: state.merchantCorrection !== initialMerchant,
  };
}

// Hook for batch merchant corrections
export function useBatchMerchantCorrection() {
  const [corrections, setCorrections] = useState<Map<string, string>>(new Map());
  const correctMutation = useCorrectTransactionMerchant();

  const addCorrection = (transactionId: string, merchantName: string) => {
    setCorrections(prev => new Map(prev).set(transactionId, merchantName));
  };

  const removeCorrection = (transactionId: string) => {
    setCorrections(prev => {
      const newMap = new Map(prev);
      newMap.delete(transactionId);
      return newMap;
    });
  };

  const clearCorrections = () => {
    setCorrections(new Map());
  };

  const saveAllCorrections = async () => {
    const results = [];
    
    for (const [transactionId, merchantName] of corrections) {
      try {
        const result = await correctMutation.mutateAsync({
          transactionId,
          merchantName,
        });
        results.push({ transactionId, success: true, result });
      } catch (error) {
        results.push({ 
          transactionId, 
          success: false, 
          error: error instanceof Error ? error.message : 'Unknown error' 
        });
      }
    }

    return results;
  };

  return {
    corrections: Array.from(corrections.entries()),
    correctionCount: corrections.size,
    addCorrection,
    removeCorrection,
    clearCorrections,
    saveAllCorrections,
    isSaving: correctMutation.isPending,
    lastResult: correctMutation.data,
    error: correctMutation.error,
  };
}

// Simple hook for inline merchant editing
export function useInlineMerchantEditor(transactionId: string, initialMerchant: string = '') {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(initialMerchant);
  const correctMutation = useCorrectTransactionMerchant();

  const startEditing = () => {
    setValue(initialMerchant);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setValue(initialMerchant);
    setIsEditing(false);
    correctMutation.reset();
  };

  const saveChanges = async () => {
    if (!value.trim() || value === initialMerchant) {
      cancelEditing();
      return;
    }

    try {
      await correctMutation.mutateAsync({
        transactionId,
        merchantName: value.trim(),
      });
      setIsEditing(false);
    } catch (error) {
      // Error handling is managed by the mutation itself
      console.error('Failed to save merchant correction:', error);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      saveChanges();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      cancelEditing();
    }
  };

  return {
    isEditing,
    value,
    setValue,
    startEditing,
    cancelEditing,
    saveChanges,
    handleKeyPress,
    isSaving: correctMutation.isPending,
    error: correctMutation.error,
    result: correctMutation.data,
    canSave: value.trim().length > 0 && value !== initialMerchant,
  };
}