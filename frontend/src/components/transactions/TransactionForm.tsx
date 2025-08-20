  import { useState, useEffect } from 'react';
  import { Button } from '../ui/Button';
  import { Input } from '../ui/Input';
  import { Modal } from '../ui/Modal';
  import { CategorySelector } from '../categories/CategorySelector';
  import { transactionService } from '../../services/transactionService';
  import { useLiveMerchantRecognition, useMerchantActions } from '../../hooks/useMerchantEnrichment';
  import type { Transaction, CreateTransactionRequest, UpdateTransactionRequest } from '../../types/transaction';
  import type { Category } from '../../types/category';

  interface TransactionFormProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: CreateTransactionRequest | UpdateTransactionRequest) => Promise<void>;
    transaction?: Transaction;
    title?: string;
  }

  export function TransactionForm({ 
    isOpen, 
    onClose, 
    onSubmit, 
    transaction,
    title = 'Add Transaction'
  }: TransactionFormProps) {
    /**
     * TODO: Migrate form state management to react-hook-form
     * 
     * Current state: This form uses manual useState management, which is inconsistent
     * with other forms in the application (BudgetForm, LoginForm, RegisterForm) that
     * use react-hook-form for better validation, error handling, and performance.
     * 
     * Migration benefits:
     * - Consistent form patterns across the application
     * - Better validation with built-in error handling
     * - Reduced re-renders and improved performance
     * - Type-safe form handling with better TypeScript integration
     * - Built-in support for form reset, dirty state, and submission states
     * 
     * Migration steps:
     * 1. Import useForm from 'react-hook-form'
     * 2. Replace useState with useForm hook:
     *    const { register, handleSubmit, formState: { errors }, reset, setValue } = useForm<CreateTransactionRequest>()
     * 3. Replace manual onChange handlers with register() calls
     * 4. Use handleSubmit wrapper for form submission
     * 5. Replace manual error state with formState.errors
     * 6. Use setValue for programmatic form updates (merchant recognition)
     * 7. Use reset() for form cleanup on close
     * 
     * Example pattern (see BudgetForm.tsx for reference):
     * const form = useForm<CreateTransactionRequest>({
     *   defaultValues: {
     *     accountId: transaction?.accountId || '',
     *     amountCents: transaction?.amountCents || 0,
     *     // ... other defaults
     *   }
     * });
     */
    const [formData, setFormData] = useState<CreateTransactionRequest>({
      accountId: transaction?.accountId || '',
      amountCents: transaction?.amountCents || 0,
      description: transaction?.description || '',
      merchant: transaction?.merchant || '',
      transactionDate: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
      transaction_type: 'expense',
      amount: transaction ? (transaction.amountCents / 100) : 0,
      transaction_date: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
      category_id: transaction?.categoryId,
    });

    const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [needsCategoryConfirmation, setNeedsCategoryConfirmation] = useState(false);
  const [suggestedCategoryId, setSuggestedCategoryId] = useState<string | undefined>();
  
  // Use the new merchant recognition hooks
  const liveMerchantRecognition = useLiveMerchantRecognition();
  const merchantActions = useMerchantActions();
 
   const validateForm = (): boolean => {
     const newErrors: Record<string, string> = {};

      if (!formData.amount || formData.amount === 0) {
        newErrors.amount = 'Amount must be greater than 0';
      }

      if (formData.description && formData.description.length > 200) {
        newErrors.description = 'Description must be less than 200 characters';
      }

      if (!formData.transaction_date) {
        newErrors.transaction_date = 'Transaction date is required';
      }

      if (!formData.transaction_type || !['income', 'expense'].includes(formData.transaction_type)) {
        newErrors.transaction_type = 'Transaction type must be income or expense';
      }

      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      
      // If we are confirming the category, don't re-validate the whole form
      if (needsCategoryConfirmation) {
        if (!formData.category_id) {
          setErrors({ submit: "Please select a category to confirm." });
          return;
        }
      } else if (!validateForm()) {
        return;
      }

      setIsSubmitting(true);
      try {
        await onSubmit(formData);
        onClose();
        // Reset form and confirmation state
        setFormData({
          accountId: '',
          amountCents: 0,
          amount: 0,
          category_id: undefined,
          description: '',
          merchant: '',
          transactionDate: new Date().toISOString().split('T')[0],
          transaction_date: new Date().toISOString().split('T')[0],
          transaction_type: 'expense',
        });
        setErrors({});
        setNeedsCategoryConfirmation(false);
        setSuggestedCategoryId(undefined);
        liveMerchantRecognition.reset();
        merchantActions.resetRecognition();
      } catch (error) {
        console.error('Failed to submit transaction:', error);
        
        // Handle low confidence from the backend
        const errorObj = error as { response?: { status: number; data: { detail: { reason: string; suggested_category_id: string; message: string } } } };
        if (errorObj.response?.status === 409) {
          const errorData = errorObj.response.data.detail;
          if (errorData.reason === 'low_confidence') {
            setNeedsCategoryConfirmation(true);
            setSuggestedCategoryId(errorData.suggested_category_id);
            setErrors({ submit: errorData.message });
            setIsSubmitting(false); // Stop submitting to allow user action
            return; 
          }
        }
        
        setErrors({ submit: 'Failed to save transaction. Please try again.' });
      } finally {
        // Only set submitting to false if we are not in the confirmation step
        if (!needsCategoryConfirmation) {
          setIsSubmitting(false);
        }
      }
    };

    const handleInputChange = (field: string, value: string | number | boolean | null) => {
      setFormData(prev => {
        const updated = { ...prev, [field]: value };
        
        // Keep amount and amountCents in sync
        if (field === 'amount') {
          updated.amountCents = Math.round((value as number) * 100);
        } else if (field === 'amountCents') {
          updated.amount = (value as number) / 100;
        }
        
        // Keep transaction dates in sync
        if (field === 'transaction_date') {
          updated.transactionDate = value as string;
        } else if (field === 'transactionDate') {
          updated.transaction_date = value as string;
        }
        
        return updated;
      });
      
      // Clear error for this field
      if (errors[field]) {
        setErrors(prev => ({ ...prev, [field]: '' }));
      }
    };

    const handleCategoryChange = (categoryId: string | undefined, _category?: Category) => {
      void _category; // intentionally unused
      setFormData(prev => ({ ...prev, category_id: categoryId }));
      if (errors.category_id) {
        setErrors(prev => ({ ...prev, category_id: '' }));
      }
    };

    const handleRecognizeMerchant = async () => {
      if (!formData.description?.trim()) {
        setErrors(prev => ({ ...prev, description: 'Please enter a description first' }));
        return;
      }

      try {
        await merchantActions.recognizeFromDescriptionAsync({ description: formData.description });
        
        if (merchantActions.recognitionResult?.recognized_merchant && 
            merchantActions.recognitionResult.confidence_score >= 0.6) {
          setFormData(prev => ({ 
            ...prev, 
            merchant: merchantActions.recognitionResult?.recognized_merchant || '' 
          }));
        }
      } catch (error) {
        console.error('Failed to recognize merchant:', error);
        setErrors(prev => ({ ...prev, merchant: 'Failed to recognize merchant. Please try again.' }));
      }
    };

    // Auto-recognize merchant when description changes (debounced)
    useEffect(() => {
      if (!formData.description?.trim() || formData.description.length < 3) {
        return;
      }

      const timeoutId = setTimeout(async () => {
        const result = await liveMerchantRecognition.recognizeFromDescription(formData.description);
        if (result?.recognized_merchant && result.confidence_score >= 0.8) {
          // Only auto-fill with high confidence
          setFormData(prev => ({ ...prev, merchant: result.recognized_merchant || '' }));
        }
      }, 500); // 500ms debounce

      return () => clearTimeout(timeoutId);
    }, [formData.description, liveMerchantRecognition]);



    return (
      <Modal isOpen={isOpen} onClose={onClose} title={title}>
      {needsCategoryConfirmation ? (
        <div className="space-y-4">
          <p className="text-sm text-[hsl(var(--text)/0.8)]">
            {errors.submit || "We couldn't automatically categorize this transaction. Please select a category below."}
          </p>
          <CategorySelector
            value={suggestedCategoryId}
            onChange={handleCategoryChange}
            transactionType={formData.transaction_type}
            placeholder="Choose a category"
            required={true}
          />
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setNeedsCategoryConfirmation(false)}
            >
              Back to Form
            </Button>
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || !formData.category_id}
            >
              {isSubmitting ? 'Saving...' : 'Confirm Category & Save'}
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* ... existing form ... */}
          {errors.submit && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600 text-sm">
              {errors.submit}
            </div>
          )}

          {/* Transaction Type */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Transaction Type
            </label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="transaction_type"
                  value="expense"
                  checked={formData.transaction_type === 'expense'}
                  onChange={(e) => handleInputChange('transaction_type', e.target.value)}
                  className="text-red-600 focus:ring-red-500"
                />
                <span className="ml-2 text-sm text-[hsl(var(--text))]">💸 Expense</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="transaction_type"
                  value="income"
                  checked={formData.transaction_type === 'income'}
                  onChange={(e) => handleInputChange('transaction_type', e.target.value)}
                  className="text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm text-[hsl(var(--text))]">💰 Income</span>
              </label>
            </div>
            {errors.transaction_type && (
              <p className="mt-1 text-sm text-red-600">{errors.transaction_type}</p>
            )}
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Amount
            </label>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={formData.amount || ''}
              onChange={(e) => handleInputChange('amount', parseFloat(e.target.value) || 0)}
              placeholder="0.00"
              className={errors.amount ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
            />
            {errors.amount && (
              <p className="mt-1 text-sm text-red-600">{errors.amount}</p>
            )}
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Category (Optional)
            </label>
            <CategorySelector
              value={formData.category_id}
              onChange={handleCategoryChange}
              transactionType={formData.transaction_type}
              placeholder="Select a category (or leave for auto-detection)"
              error={errors.category_id}
              required={false}
              className={errors.category_id ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
            />
            {errors.category_id && (
              <p className="mt-1 text-sm text-red-600">{errors.category_id}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Description (Optional)
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Add a note about this transaction..."
              rows={3}
              maxLength={200}
              className={`w-full px-3 py-2 border border-[hsl(var(--border))] rounded-lg focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] ${
                errors.description ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/30' : ''
              }`}
            />
            <div className="flex justify-between mt-1">
              {errors.description && (
                <p className="text-sm text-red-600">{errors.description}</p>
              )}
              <p className="text-xs text-[hsl(var(--text)/0.6)] ml-auto">
                {formData.description?.length || 0}/200
              </p>
            </div>
          </div>

          {/* Merchant */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Merchant (Optional)
            </label>
            <div className="flex space-x-2">
              <Input
                type="text"
                value={formData.merchant || ''}
                onChange={(e) => handleInputChange('merchant', e.target.value)}
                placeholder="Enter merchant name..."
                className={errors.merchant ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleRecognizeMerchant}
                disabled={merchantActions.isRecognizing || !formData.description?.trim()}
                className="shrink-0"
              >
                {merchantActions.isRecognizing ? '🔄' : '🔍'} Recognize
              </Button>
            </div>
            {(merchantActions.recognitionResult || liveMerchantRecognition.lastResult) && (
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-sm">
                {(() => {
                  const result = merchantActions.recognitionResult || liveMerchantRecognition.lastResult;
                  return result?.recognized_merchant ? (
                    <div className="space-y-1">
                      <p>
                        <span className="font-medium">Recognized:</span> {result.recognized_merchant}
                        <span className="text-gray-500 ml-2">
                          ({Math.round(result.confidence_score * 100)}% confidence)
                        </span>
                      </p>
                      {result.method_used && (
                        <p className="text-xs text-gray-500">
                          Method: {result.method_used}
                        </p>
                      )}
                      {result.suggestions && result.suggestions.length > 0 && (
                        <div className="mt-1">
                          <p className="text-xs text-gray-600 mb-1">Other suggestions:</p>
                          <div className="flex flex-wrap gap-1">
                            {result.suggestions.slice(0, 3).map((suggestion, index) => (
                              <button
                                key={index}
                                type="button"
                                onClick={() => setFormData(prev => ({ ...prev, merchant: suggestion }))}
                                className="px-2 py-0.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border"
                              >
                                {suggestion}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-600">No merchant recognized from description</p>
                  );
                })()}
              </div>
            )}
            {liveMerchantRecognition.isRecognizing && (
              <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-600">
                <span className="inline-flex items-center">
                  <span className="animate-spin mr-2">🔄</span>
                  Auto-recognizing merchant...
                </span>
              </div>
            )}
            {errors.merchant && (
              <p className="mt-1 text-sm text-red-600">{errors.merchant}</p>
            )}
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Transaction Date
            </label>
            <Input
              type="date"
              value={formData.transaction_date}
              onChange={(e) => handleInputChange('transaction_date', e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className={errors.transaction_date ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
            />
            {errors.transaction_date && (
              <p className="mt-1 text-sm text-red-600">{errors.transaction_date}</p>
            )}
          </div>

          {/* Form Actions */}
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className={formData.transaction_type === 'income' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
            >
              {isSubmitting ? 'Saving...' : transaction ? 'Update Transaction' : 'Add Transaction'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
    );
  }