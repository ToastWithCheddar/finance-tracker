import React, { useState, useEffect } from 'react';
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
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    target_amount_cents: '',
    goal_type: 'savings',
    priority: 'medium',
    target_date: '',
    contribution_frequency: '',
    monthly_target_cents: '',
    auto_contribute: false,
    auto_contribution_amount_cents: '',
    auto_contribution_source: '',
    milestone_percentage: '25',
  });

  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const { data: options } = useGoalOptions();

  const isEditing = !!goal;
  const isLoading = createGoal.isPending || updateGoal.isPending;

  // Initialize form data when goal changes
  useEffect(() => {
    if (goal) {
      setFormData({
        name: goal.name,
        description: goal.description || '',
        target_amount_cents: goal.target_amount_cents.toString(),
        goal_type: goal.goal_type,
        priority: goal.priority,
        target_date: goal.target_date ? goal.target_date.split('T')[0] : '',
        contribution_frequency: goal.contribution_frequency || '',
        monthly_target_cents: goal.monthly_target_cents?.toString() || '',
        auto_contribute: goal.auto_contribute,
        auto_contribution_amount_cents: goal.auto_contribution_amount_cents?.toString() || '',
        auto_contribution_source: goal.auto_contribution_source || '',
        milestone_percentage: goal.milestone_percentage.toString(),
      });
    } else {
      // Reset form for new goal
      setFormData({
        name: '',
        description: '',
        target_amount_cents: '',
        goal_type: 'savings',
        priority: 'medium',
        target_date: '',
        contribution_frequency: '',
        monthly_target_cents: '',
        auto_contribute: false,
        auto_contribution_amount_cents: '',
        auto_contribution_source: '',
        milestone_percentage: '25',
      });
    }
  }, [goal, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const baseData = {
        name: formData.name,
        description: formData.description || undefined,
        target_amount_cents: Math.round(parseFloat(formData.target_amount_cents) * 100),
        goal_type: formData.goal_type as Goal['goal_type'],
        priority: formData.priority as Goal['priority'],
        target_date: formData.target_date || undefined,
        contribution_frequency: formData.contribution_frequency || undefined,
        monthly_target_cents: formData.monthly_target_cents ? Math.round(parseFloat(formData.monthly_target_cents) * 100) : undefined,
        auto_contribute: formData.auto_contribute,
        auto_contribution_amount_cents: formData.auto_contribution_amount_cents ? 
          Math.round(parseFloat(formData.auto_contribution_amount_cents) * 100) : undefined,
        auto_contribution_source: formData.auto_contribution_source || undefined,
        milestone_percentage: parseFloat(formData.milestone_percentage),
      };

      if (isEditing) {
        await updateGoal.mutateAsync({
          goalId: goal.id,
          goalData: baseData as GoalUpdate,
        });
      } else {
        await createGoal.mutateAsync(baseData as GoalCreate);
      }

      onSuccess?.();
      onClose();
    } catch {
      // Error handling is done in the hooks
    }
  };

  const handleInputChange = (field: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const calculateMonthlyTarget = () => {
    const targetAmount = Math.round(parseFloat(formData.target_amount_cents) * 100);
    const targetDate = formData.target_date;
    
    if (targetAmount && targetDate) {
      const now = new Date();
      const target = new Date(targetDate);
      const monthsRemaining = Math.max(1, 
        (target.getFullYear() - now.getFullYear()) * 12 + 
        (target.getMonth() - now.getMonth())
      );
      
      const currentAmount = goal?.current_amount_cents || 0;
      const remaining = targetAmount - currentAmount;
      const monthlyTarget = remaining / monthsRemaining;
      
      setFormData(prev => ({
        ...prev,
        monthly_target_cents: monthlyTarget.toFixed(2)
      }));
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Goal' : 'Create New Goal'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Basic Information</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Goal Name *
              </label>
              <Input
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="e.g., Emergency Fund, New Car, Vacation"
                required
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Goal Type *
              </label>
              <select
                value={formData.goal_type}
                onChange={(e) => handleInputChange('goal_type', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
                required
              >
                {options?.goal_types.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.icon} {type.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => handleInputChange('priority', e.target.value)}
                className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
              >
                {options?.priorities.map((priority) => (
                  <option key={priority.value} value={priority.value}>
                    {priority.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Target Amount *
              </label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={formData.target_amount_cents}
                onChange={(e) => handleInputChange('target_amount_cents', e.target.value)}
                placeholder="0.00"
                required
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Target Date
              </label>
              <Input
                type="date"
                value={formData.target_date}
                onChange={(e) => handleInputChange('target_date', e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="w-full"
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Optional description of your goal..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.monthly_target_cents}
                  onChange={(e) => handleInputChange('monthly_target_cents', e.target.value)}
                  placeholder="0.00"
                  className="flex-1"
                />
                <Button
                  type="button"
                  onClick={calculateMonthlyTarget}
                  variant="outline"
                  disabled={!formData.target_amount_cents || !formData.target_date}
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
                value={formData.milestone_percentage}
                onChange={(e) => handleInputChange('milestone_percentage', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="10">Every 10%</option>
                <option value="25">Every 25%</option>
                <option value="50">Every 50%</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                How often to celebrate milestones
              </p>
            </div>
          </div>
        </Card>

        {/* Automatic Contributions */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Automatic Contributions</h3>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="auto_contribute"
                checked={formData.auto_contribute}
                onChange={(e) => handleInputChange('auto_contribute', e.target.checked)}
                className="rounded border-[hsl(var(--border))] text-[hsl(var(--brand))] focus:ring-[hsl(var(--brand))]"
              />
              <label htmlFor="auto_contribute" className="text-sm font-medium text-[hsl(var(--text))]">
                Enable automatic contributions
              </label>
            </div>
            
            {formData.auto_contribute && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 ml-6">
                <div>
                  <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                    Amount
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.auto_contribution_amount_cents}
                    onChange={(e) => handleInputChange('auto_contribution_amount_cents', e.target.value)}
                    placeholder="0.00"
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                    Frequency
                  </label>
                  <select
                    value={formData.contribution_frequency}
                    onChange={(e) => handleInputChange('contribution_frequency', e.target.value)}
                    className="w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-[hsl(var(--brand))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))]"
                  >
                    <option value="">Select frequency</option>
                    {options?.frequencies.map((freq) => (
                      <option key={freq.value} value={freq.value}>
                        {freq.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1 text-[hsl(var(--text))] opacity-80">
                    Source Account
                  </label>
                  <Input
                    value={formData.auto_contribution_source}
                    onChange={(e) => handleInputChange('auto_contribution_source', e.target.value)}
                    placeholder="e.g., Checking Account"
                    className="w-full"
                  />
                </div>
              </div>
            )}
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
            disabled={isLoading || !formData.name || !formData.target_amount_cents}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isLoading ? 'Saving...' : isEditing ? 'Update Goal' : 'Create Goal'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}