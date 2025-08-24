import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Card } from '../ui/Card';
import { useCreateGoal, useUpdateGoal, useGoalOptions } from '../../hooks/useGoals';
import type { Goal, GoalCreate, GoalUpdate } from '../../types/goals';

interface GoalFormProps {
  goal?: Goal;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function GoalForm({ goal, isOpen, onClose, onSuccess }: GoalFormProps) {
  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const { data: options } = useGoalOptions();

  const isEditing = !!goal;
  const isLoading = createGoal.isPending || updateGoal.isPending;

  // Local state for friendly currency input handling
  const [targetAmountInput, setTargetAmountInput] = useState<string>('');
  const [monthlyTargetInput, setMonthlyTargetInput] = useState<string>('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
    control
  } = useForm<GoalCreate>();

  // Format currency for display
  const formatCurrencyDisplay = (cents: number): string => {
    return (cents / 100).toFixed(2);
  };

  // Parse currency input to cents
  const parseCurrencyInput = (input: string): number => {
    // Remove any non-numeric characters except decimal point
    const cleaned = input.replace(/[^\d.]/g, '');
    const numericValue = parseFloat(cleaned);
    return isNaN(numericValue) ? 0 : Math.round(numericValue * 100);
  };

  // Initialize form data when goal changes
  useEffect(() => {
    if (isOpen) {
      if (goal) {
        // Edit mode - populate form with goal data
        reset({
          name: goal.name,
          description: goal.description || '',
          target_amount_cents: goal.target_amount_cents,
          goal_type: goal.goal_type,
          priority: goal.priority,
          target_date: goal.target_date ? goal.target_date.split('T')[0] : '',
          monthly_target_cents: goal.monthly_target_cents || 0,
          milestone_percentage: goal.milestone_percentage,
        });
        setTargetAmountInput(formatCurrencyDisplay(goal.target_amount_cents));
        setMonthlyTargetInput(goal.monthly_target_cents ? formatCurrencyDisplay(goal.monthly_target_cents) : '');
      } else {
        // Create mode - reset to defaults
        reset({
          name: '',
          description: '',
          target_amount_cents: 0,
          goal_type: 'SAVINGS',
          priority: 'MEDIUM',
          target_date: '',
          monthly_target_cents: 0,
          milestone_percentage: 25,
        });
        setTargetAmountInput('');
        setMonthlyTargetInput('');
      }
    }
  }, [goal, isOpen, reset]);

  const onFormSubmit = async (data: GoalCreate) => {
    try {
      // Clean up the data and ensure proper types
      const cleanData = {
        name: data.name,
        description: data.description || undefined,
        target_amount_cents: data.target_amount_cents,
        goal_type: data.goal_type,
        priority: data.priority,
        target_date: data.target_date || undefined,
        monthly_target_cents: data.monthly_target_cents || undefined,
        milestone_percentage: data.milestone_percentage,
      };

      console.log('Submitting goal data:', cleanData);

      if (isEditing) {
        await updateGoal.mutateAsync({
          goalId: goal.id,
          goalData: cleanData as GoalUpdate,
        });
      } else {
        await createGoal.mutateAsync(cleanData);
      }

      onSuccess?.();
      onClose();
    } catch (error) {
      console.error('Goal submission error:', error);
      // Error handling is done in the hooks, but let's also log for debugging
    }
  };


  const calculateMonthlyTarget = () => {
    console.log('🔢 Calculate button clicked');
    
    const targetAmount = parseCurrencyInput(targetAmountInput);
    const targetDate = watchedTargetDate; // Use the watched value instead of calling watch again
    
    console.log('📊 Calculation inputs:', {
      targetAmountInput: targetAmountInput,
      targetAmount: targetAmount,
      targetDate: targetDate,
      watchedTargetDate: watchedTargetDate
    });
    
    if (!targetAmount || targetAmount <= 0) {
      console.log('❌ Invalid target amount:', targetAmount);
      return;
    }
    
    if (!targetDate) {
      console.log('❌ No target date provided');
      return;
    }
    
    const now = new Date();
    const target = new Date(targetDate);
    
    console.log('📅 Date comparison:', {
      now: now.toISOString(),
      target: target.toISOString(),
      isTargetInFuture: target > now
    });
    
    if (target <= now) {
      console.log('❌ Target date is in the past or today');
      return;
    }
    
    const monthsRemaining = Math.max(1, 
      (target.getFullYear() - now.getFullYear()) * 12 + 
      (target.getMonth() - now.getMonth())
    );
    
    const currentAmount = goal?.current_amount_cents || 0;
    const remaining = targetAmount - currentAmount;
    const monthlyTargetCents = Math.max(0, Math.round(remaining / monthsRemaining));
    
    console.log('💰 Calculation results:', {
      currentAmount: currentAmount,
      remaining: remaining,
      monthsRemaining: monthsRemaining,
      monthlyTargetCents: monthlyTargetCents,
      monthlyTargetDollars: monthlyTargetCents / 100
    });
    
    setMonthlyTargetInput(formatCurrencyDisplay(monthlyTargetCents));
    setValue('monthly_target_cents', monthlyTargetCents);
    
    console.log('✅ Monthly target updated successfully');
  };

  // Watch target date for button enabling
  const watchedTargetDate = watch('target_date');
  
  // Debug button state
  const isButtonDisabled = !targetAmountInput || !watchedTargetDate || isLoading;
  
  // Debug state changes
  useEffect(() => {
    console.log('🔘 Button state debug:', {
      targetAmountInput: targetAmountInput,
      watchedTargetDate: watchedTargetDate,
      isLoading: isLoading,
      isButtonDisabled: isButtonDisabled
    });
  }, [targetAmountInput, watchedTargetDate, isLoading, isButtonDisabled]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Goal' : 'Create New Goal'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
        {/* Basic Information */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Basic Information</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Goal Name *
              </label>
              <Input
                {...register('name', { 
                  required: 'Goal name is required',
                  minLength: { value: 1, message: 'Goal name cannot be empty' }
                })}
                placeholder="e.g., Emergency Fund, New Car, Vacation"
                disabled={isLoading}
                className="w-full"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Goal Type *
              </label>
              <select
                {...register('goal_type', { required: 'Please select a goal type' })}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
                disabled={isLoading}
              >
                {options?.goal_types ? (
                  options.goal_types.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.icon} {type.label}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="SAVINGS">💰 Savings</option>
                    <option value="DEBT_PAYOFF">💳 Debt Payoff</option>
                    <option value="EMERGENCY_FUND">🚨 Emergency Fund</option>
                    <option value="INVESTMENT">📈 Investment</option>
                    <option value="PURCHASE">🛍️ Purchase</option>
                    <option value="OTHER">🎯 Other</option>
                  </>
                )}
              </select>
              {errors.goal_type && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.goal_type.message}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Priority
              </label>
              <select
                {...register('priority')}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
                disabled={isLoading}
              >
                {options?.priorities ? (
                  options.priorities.map((priority) => (
                    <option key={priority.value} value={priority.value}>
                      {priority.label}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </>
                )}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Target Amount *
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[hsl(var(--text))] opacity-70">
                  $
                </span>
                <Controller
                  name="target_amount_cents"
                  control={control}
                  rules={{ 
                    required: 'Target amount is required',
                    min: { value: 1, message: 'Amount must be greater than 0' }
                  }}
                  render={({ field: { onChange, onBlur } }) => (
                    <Input
                      type="text"
                      inputMode="decimal"
                      pattern="^\d*\.?\d{0,2}$"
                      value={targetAmountInput}
                      onChange={(e) => {
                        const input = e.target.value;
                        // Allow only digits and a single decimal point with up to 2 decimals
                        if (/^\d*(?:\.\d{0,2})?$/.test(input)) {
                          setTargetAmountInput(input);
                          const cents = parseCurrencyInput(input);
                          onChange(cents);
                        }
                      }}
                      onBlur={() => {
                        // Format on blur for better UX
                        const cents = parseCurrencyInput(targetAmountInput);
                        setTargetAmountInput(cents ? formatCurrencyDisplay(cents) : '');
                        onChange(cents);
                        onBlur();
                      }}
                      className="w-full pl-8"
                      placeholder="0.00"
                      disabled={isLoading}
                    />
                  )}
                />
              </div>
              {errors.target_amount_cents && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.target_amount_cents.message}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Target Date
              </label>
              <Input
                type="date"
                {...register('target_date')}
                min={new Date().toISOString().split('T')[0]}
                className="w-full"
                disabled={isLoading}
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Description
              </label>
              <textarea
                {...register('description')}
                placeholder="Optional description of your goal..."
                rows={3}
                className="w-full px-3 py-2 border border-[hsl(var(--border))] rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))]"
                disabled={isLoading}
              />
            </div>
          </div>
        </Card>

        {/* Progress Tracking */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Progress Tracking</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Monthly Target
              </label>
              <div className="flex space-x-2">
                <div className="relative flex-1">
                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[hsl(var(--text))] opacity-70">
                    $
                  </span>
                  <Controller
                    name="monthly_target_cents"
                    control={control}
                    render={({ field: { onChange, onBlur } }) => (
                      <Input
                        type="text"
                        inputMode="decimal"
                        pattern="^\d*\.?\d{0,2}$"
                        value={monthlyTargetInput}
                        onChange={(e) => {
                          const input = e.target.value;
                          // Allow only digits and a single decimal point with up to 2 decimals
                          if (/^\d*(?:\.\d{0,2})?$/.test(input)) {
                            setMonthlyTargetInput(input);
                            const cents = parseCurrencyInput(input);
                            onChange(cents);
                          }
                        }}
                        onBlur={() => {
                          // Format on blur for better UX
                          const cents = parseCurrencyInput(monthlyTargetInput);
                          setMonthlyTargetInput(cents ? formatCurrencyDisplay(cents) : '');
                          onChange(cents);
                          onBlur();
                        }}
                        className="pl-8"
                        placeholder="0.00"
                        disabled={isLoading}
                      />
                    )}
                  />
                </div>
                <Button
                  type="button"
                  onClick={() => {
                    console.log('🖱️ Calculate button clicked (onClick handler)');
                    calculateMonthlyTarget();
                  }}
                  variant="outline"
                  disabled={isButtonDisabled}
                >
                  Calculate
                </Button>
              </div>
              <p className="text-xs mt-1 text-[hsl(var(--text))] opacity-70">
                Amount to save each month to reach your goal
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Milestone Percentage
              </label>
              <select
                {...register('milestone_percentage')}
                className="w-full px-3 py-2 border border-[hsl(var(--border))] rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))]"
                disabled={isLoading}
              >
                <option value={10}>Every 10%</option>
                <option value={25}>Every 25%</option>
                <option value={50}>Every 50%</option>
              </select>
              <p className="text-xs mt-1 text-[hsl(var(--text))] opacity-70">
                How often to celebrate milestones
              </p>
            </div>
          </div>
        </Card>


        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-[hsl(var(--border))]">
          <Button
            type="button"
            onClick={onClose}
            variant="outline"
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isLoading ? 'Saving...' : isEditing ? 'Update Goal' : 'Create Goal'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}