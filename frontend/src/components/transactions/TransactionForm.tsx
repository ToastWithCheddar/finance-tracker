import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { X } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { CurrencyInput } from '../ui/CurrencyInput';
import { Modal } from '../ui/Modal';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { CategorySelector } from '../categories/CategorySelector';
import { transactionService } from '../../services/transactionService';
import { useAccounts } from '../../hooks/useAccounts';
  
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
        transaction_type: transaction ? (transaction.amountCents < 0 ? 'expense' : 'income') : 'expense',
        amount: transaction ? Math.abs(transaction.amountCents / 100) : 0,
        transaction_date: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
        category_id: transaction?.categoryId,
      }
    });

    // Watch form values for real-time updates
    const watchedValues = watch();
    const [submitError, setSubmitError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Load accounts for selector
  const { data: accounts = [], isLoading: accountsLoading } = useAccounts();
  
  // Reset form when transaction changes or modal opens/closes
  useEffect(() => {
    if (isOpen) {
      // Set default account to first available account if not editing
      const defaultAccountId = transaction?.accountId || (accounts.length > 0 ? accounts[0].id : '');
      
      reset({
        accountId: defaultAccountId,
        amountCents: transaction?.amountCents || 0,
        description: transaction?.description || '',
        merchant: transaction?.merchant || '',
        transactionDate: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
        transaction_type: transaction ? (transaction.amountCents < 0 ? 'expense' : 'income') : 'expense',
        amount: transaction ? Math.abs(transaction.amountCents / 100) : 0,
        transaction_date: transaction?.transactionDate?.split('T')[0] || new Date().toISOString().split('T')[0],
        category_id: transaction?.categoryId,
      });
      setNeedsCategoryConfirmation(false);
      setSuggestedCategoryId(undefined);
      setSubmitError('');

    }
  }, [isOpen, transaction, reset, accounts]);
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
        // Prepare payload with correct sign for amountCents and canonical field names
        const cents = Math.round((formData.amount || 0) * 100);
        const signedAmountCents = (formData.transaction_type === 'expense')
          ? -Math.abs(cents)
          : Math.abs(cents);

        const submissionData: CreateTransactionRequest = {
          accountId: formData.accountId,
          amountCents: signedAmountCents,
          description: formData.description || '',
          merchant: formData.merchant,
          transactionDate: formData.transaction_date, // send camelCase; service will normalize if needed
          categoryId: formData.category_id,
          transaction_type: formData.transaction_type,
          notes: formData.notes,
          tags: formData.tags,
        } as CreateTransactionRequest;

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
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {title}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          
          <CardContent>
            {needsCategoryConfirmation ? (
              <div className="space-y-4">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {submitError || "We couldn't automatically categorize this transaction. Please select a category below."}
                </p>
                <CategorySelector
                  value={suggestedCategoryId}
                  onChange={handleCategoryChange}
                  transactionType={watchedValues.transaction_type}
                  placeholder="Choose a category"
                  required={true}
                />
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-600">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setNeedsCategoryConfirmation(false)}
                    disabled={isSubmitting}
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
              <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
                {/* Form error display */}
                {submitError && (
                  <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
                    {submitError}
                  </div>
                )}

                {/* Account Selection */}
                <div>
                  <label htmlFor="accountId" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Account *
                  </label>
                  <select
                    id="accountId"
                    {...register('accountId', {
                      required: 'Please select an account'
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    disabled={accountsLoading}
                  >
                    <option value="">Select an account...</option>
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name} ({account.account_type}) - ${(account.balance_cents / 100).toFixed(2)}
                      </option>
                    ))}
                  </select>
                  {errors.accountId && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.accountId.message}</p>
                  )}
                  {accountsLoading && (
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Loading accounts...</p>
                  )}
                </div>

                {/* Transaction Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
                        className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 dark:border-gray-600"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">💸 Expense</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        {...register('transaction_type', { 
                          required: 'Transaction type is required' 
                        })}
                        type="radio"
                        value="income"
                        className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 dark:border-gray-600"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">💰 Income</span>
                    </label>
                  </div>
                  {errors.transaction_type && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.transaction_type.message}</p>
                  )}
                </div>

                {/* Amount */}
                <div>
                  <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Amount
                  </label>
                  <Controller
                    name="amount"
                    control={control}
                    rules={{ 
                      required: 'Amount is required',
                      min: { value: 0.01, message: 'Amount must be greater than 0' }
                    }}
                    render={({ field: { onChange, onBlur, value } }) => (
                      <CurrencyInput
                        id="amount"
                        value={value ? Math.round(value * 100) : 0}
                        onChange={(cents) => onChange(cents / 100)}
                        onBlur={onBlur}
                        error={errors.amount?.message}
                        disabled={isSubmitting}
                      />
                    )}
                  />
                  {errors.amount && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.amount.message}</p>
                  )}
                </div>

                {/* Category */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.category_id.message}</p>
                  )}
                </div>

                {/* Description */}
                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Description (Optional)
                  </label>
                  <textarea
                    id="description"
                    {...register('description', {
                      maxLength: { value: 200, message: 'Description must be less than 200 characters' }
                    })}
                    placeholder="Add a note about this transaction..."
                    rows={3}
                    maxLength={200}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    disabled={isSubmitting}
                  />
                  <div className="flex justify-between mt-1">
                    {errors.description && (
                      <p className="text-sm text-red-600 dark:text-red-400">{errors.description.message}</p>
                    )}
                    <p className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                      {watchedValues.description?.length || 0}/200
                    </p>
                  </div>
                </div>

                {/* Merchant */}
                <div>
                  <label htmlFor="merchant" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Merchant (Optional)
                  </label>
                  <Input
                    id="merchant"
                    {...register('merchant')}
                    type="text"
                    placeholder="Enter merchant name..."
                    disabled={isSubmitting}
                  />
                  {errors.merchant && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.merchant.message}</p>
                  )}
                </div>

                {/* Date */}
                <div>
                  <label htmlFor="transaction_date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Transaction Date
                  </label>
                  <Input
                    id="transaction_date"
                    {...register('transaction_date', {
                      required: 'Transaction date is required'
                    })}
                    type="date"
                    max={new Date().toISOString().split('T')[0]}
                    disabled={isSubmitting}
                  />
                  {errors.transaction_date && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.transaction_date.message}</p>
                  )}
                </div>

          

                {/* Form Actions */}
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-600">
                  <Button
                    type="button"
                    variant="ghost"
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
          </CardContent>
        </Card>
      </Modal>
    );
  }
