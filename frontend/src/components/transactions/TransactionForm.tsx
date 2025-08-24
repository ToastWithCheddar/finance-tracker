  import { useState, useEffect } from 'react';
  import { useForm, Controller } from 'react-hook-form';
  import { Button } from '../ui/Button';
  import { Input } from '../ui/Input';
  import { Modal } from '../ui/Modal';
  import { CategorySelector } from '../categories/CategorySelector';
  import { transactionService } from '../../services/transactionService';
  
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
    // React Hook Form setup
    const {
      register,
      handleSubmit,
      formState: { errors },
      reset,
      setValue,
      watch,
      control
    } = useForm<CreateTransactionRequest>({
      defaultValues: {
        accountId: transaction?.accountId || '',
        amountCents: transaction?.amountCents || 0,
        description: transaction?.description || '',
        merchant: transaction?.merchant || '',
        transactionDate: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
        transaction_type: 'expense',
        amount: transaction ? (transaction.amountCents / 100) : 0,
        transaction_date: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
        category_id: transaction?.categoryId,
      }
    });

    // Watch form values for real-time updates
    const watchedValues = watch();
    const [submitError, setSubmitError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Reset form when transaction changes or modal opens/closes
  useEffect(() => {
    if (isOpen) {
      reset({
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
      setNeedsCategoryConfirmation(false);
      setSuggestedCategoryId(undefined);
      setSubmitError('');

    }
  }, [isOpen, transaction, reset]);
  const [needsCategoryConfirmation, setNeedsCategoryConfirmation] = useState(false);
  const [suggestedCategoryId, setSuggestedCategoryId] = useState<string | undefined>();
  

 
   // Form validation is now handled by react-hook-form through register options

    const onFormSubmit = async (formData: CreateTransactionRequest) => {
      // If we are confirming the category, don't re-validate the whole form
      if (needsCategoryConfirmation) {
        if (!watchedValues.category_id) {
          setSubmitError("Please select a category to confirm.");
          return;
        }
      }

      setIsSubmitting(true);
      try {
        // Sync amount fields before submission
        const submissionData = {
          ...formData,
          amountCents: Math.round(formData.amount * 100),
          transactionDate: formData.transaction_date,
        };
        
        await onSubmit(submissionData);
        onClose();
        
        // Reset form and confirmation state
        reset();
        setNeedsCategoryConfirmation(false);
        setSuggestedCategoryId(undefined);
        setSubmitError('');

      } catch (error) {
        console.error('Failed to submit transaction:', error);
        
        // Handle low confidence from the backend
        const errorObj = error as { response?: { status: number; data: { detail: { reason: string; suggested_category_id: string; message: string } } } };
        if (errorObj.response?.status === 409) {
          const errorData = errorObj.response.data.detail;
          if (errorData.reason === 'low_confidence') {
            setNeedsCategoryConfirmation(true);
            setSuggestedCategoryId(errorData.suggested_category_id);
            setSubmitError(errorData.message);
            setIsSubmitting(false); // Stop submitting to allow user action
            return; 
          }
        }
        
        setSubmitError('Failed to save transaction. Please try again.');
      } finally {
        // Only set submitting to false if we are not in the confirmation step
        if (!needsCategoryConfirmation) {
          setIsSubmitting(false);
        }
      }
    };

    // Handle confirmation step submission
    const handleConfirmSubmit = () => {
      if (!watchedValues.category_id) {
        setSubmitError("Please select a category to confirm.");
        return;
      }
      onFormSubmit(watchedValues);
    };

    // Sync amount when it changes (for real-time updates)
    useEffect(() => {
      if (watchedValues.amount !== undefined) {
        setValue('amountCents', Math.round(watchedValues.amount * 100));
      }
    }, [watchedValues.amount, setValue]);

    // Sync transaction_date when it changes
    useEffect(() => {
      if (watchedValues.transaction_date) {
        setValue('transactionDate', watchedValues.transaction_date);
      }
    }, [watchedValues.transaction_date, setValue]);

    const handleCategoryChange = (categoryId: string | undefined, _category?: Category) => {
      void _category; // intentionally unused
      setValue('category_id', categoryId);
    };





    return (
      <Modal isOpen={isOpen} onClose={onClose} title={title}>
      {needsCategoryConfirmation ? (
        <div className="space-y-4">
          <p className="text-sm text-[hsl(var(--text)/0.8)]">
            {submitError || "We couldn't automatically categorize this transaction. Please select a category below."}
          </p>
          <CategorySelector
            value={suggestedCategoryId}
            onChange={handleCategoryChange}
            transactionType={watchedValues.transaction_type}
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
              onClick={handleConfirmSubmit}
              disabled={isSubmitting || !watchedValues.category_id}
            >
              {isSubmitting ? 'Saving...' : 'Confirm Category & Save'}
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
          {/* Form error display */}
          {submitError && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600 text-sm">
              {submitError}
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
                  {...register('transaction_type', { 
                    required: 'Transaction type is required' 
                  })}
                  type="radio"
                  value="expense"
                  className="text-red-600 focus:ring-red-500"
                />
                <span className="ml-2 text-sm text-[hsl(var(--text))]">💸 Expense</span>
              </label>
              <label className="flex items-center">
                <input
                  {...register('transaction_type', { 
                    required: 'Transaction type is required' 
                  })}
                  type="radio"
                  value="income"
                  className="text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm text-[hsl(var(--text))]">💰 Income</span>
              </label>
            </div>
            {errors.transaction_type && (
              <p className="mt-1 text-sm text-red-600">{errors.transaction_type.message}</p>
            )}
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Amount
            </label>
            <Input
              {...register('amount', {
                required: 'Amount is required',
                min: { value: 0.01, message: 'Amount must be greater than 0' },
                valueAsNumber: true
              })}
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              className={errors.amount ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
            />
            {errors.amount && (
              <p className="mt-1 text-sm text-red-600">{errors.amount.message}</p>
            )}
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Category (Optional)
            </label>
            <Controller
              name="category_id"
              control={control}
              render={({ field }) => (
                <CategorySelector
                  value={field.value}
                  onChange={(categoryId) => field.onChange(categoryId)}
                  transactionType={watchedValues.transaction_type}
                  placeholder="Select a category (or leave for auto-detection)"
                  error={errors.category_id?.message}
                  required={false}
                  className={errors.category_id ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
                />
              )}
            />
            {errors.category_id && (
              <p className="mt-1 text-sm text-red-600">{errors.category_id.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Description (Optional)
            </label>
            <textarea
              {...register('description', {
                maxLength: { value: 200, message: 'Description must be less than 200 characters' }
              })}
              placeholder="Add a note about this transaction..."
              rows={3}
              maxLength={200}
              className={`w-full px-3 py-2 border border-[hsl(var(--border))] rounded-lg focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] ${
                errors.description ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/30' : ''
              }`}
            />
            <div className="flex justify-between mt-1">
              {errors.description && (
                <p className="text-sm text-red-600">{errors.description.message}</p>
              )}
              <p className="text-xs text-[hsl(var(--text)/0.6)] ml-auto">
                {watchedValues.description?.length || 0}/200
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
                {...register('merchant')}
                type="text"
                placeholder="Enter merchant name..."
                className={errors.merchant ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
              />

            </div>

            {errors.merchant && (
              <p className="mt-1 text-sm text-red-600">{errors.merchant.message}</p>
            )}
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
              Transaction Date
            </label>
            <Input
              {...register('transaction_date', {
                required: 'Transaction date is required'
              })}
              type="date"
              max={new Date().toISOString().split('T')[0]}
              className={errors.transaction_date ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
            />
            {errors.transaction_date && (
              <p className="mt-1 text-sm text-red-600">{errors.transaction_date.message}</p>
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
              className={watchedValues.transaction_type === 'income' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
            >
              {isSubmitting ? 'Saving...' : transaction ? 'Update Transaction' : 'Add Transaction'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
    );
  }