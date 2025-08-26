import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Target, DollarSign } from 'lucide-react';
import { useGoals, useAddContribution } from '../../hooks/useGoals';
import { formatCurrency } from '../../utils/currency';
import { goalService } from '../../services/goalService';
import { GoalStatus } from '../../types/goals';
import type { GoalContributionCreate } from '../../types/goals';

export function QuickContributionCard() {
  const [selectedGoalId, setSelectedGoalId] = useState('');
  const [amount, setAmount] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const { data: goalsData } = useGoals({ status: GoalStatus.ACTIVE });
  const addContribution = useAddContribution();

  const activeGoals = goalsData?.goals?.filter(goal => 
    goal.status === GoalStatus.ACTIVE && !goal.is_completed
  ) || [];

  const selectedGoal = activeGoals.find(goal => goal.id === selectedGoalId);

  const handleContribution = async () => {
    if (!selectedGoalId || !amount || parseFloat(amount) <= 0) return;

    setIsProcessing(true);
    try {
      const contributionData: GoalContributionCreate = {
        amount_cents: Math.round(parseFloat(amount) * 100),
      };

      await addContribution.mutateAsync({
        goalId: selectedGoalId,
        contributionData,
      });

      // Clear form after successful contribution
      setAmount('');
      setSelectedGoalId('');
    } finally {
      setIsProcessing(false);
    }
  };

  const previewProgress = selectedGoal ? 
    Math.min(((selectedGoal.current_amount_cents + Math.round((parseFloat(amount) || 0) * 100)) / selectedGoal.target_amount_cents) * 100, 100) : 0;

  if (activeGoals.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Quick Contribution</h3>
        <div className="text-center py-8">
          <div className="mb-4 flex justify-center">
            <Target className="h-16 w-16 text-blue-500" />
          </div>
          <p className="text-[hsl(var(--text))] opacity-70 mb-4">
            No active goals available for contributions.
          </p>
          <p className="text-sm text-[hsl(var(--text))] opacity-60">
            Create a new goal to start contributing!
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 bg-success-gradient border-green-200 dark:border-green-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[hsl(var(--text))]">Quick Contribution</h3>
<DollarSign className="h-6 w-6 text-green-600" />
      </div>
      
      <p className="text-sm text-[hsl(var(--text))] opacity-70 mb-4">
        Add money to your goals quickly and easily
      </p>

      <div className="space-y-4">
        {/* Goal Selection */}
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
            Select Goal
          </label>
          <select
            value={selectedGoalId}
            onChange={(e) => setSelectedGoalId(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface))] text-[hsl(var(--text))] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="">Choose a goal to contribute to...</option>
            {activeGoals.map((goal) => {
              const typeInfo = goalService.getGoalTypeInfo(goal.goal_type);
              return (
                <option key={goal.id} value={goal.id}>
                  {goal.name} - {formatCurrency(goal.current_amount_cents)} / {formatCurrency(goal.target_amount_cents)}
                </option>
              );
            })}
          </select>
        </div>

        {/* Amount Input */}
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
            Contribution Amount
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[hsl(var(--text))] opacity-60">$</span>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="pl-8 text-lg font-semibold"
              disabled={!selectedGoalId}
            />
          </div>
        </div>


        {/* Progress Preview */}
        {selectedGoal && amount && parseFloat(amount) > 0 && (
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-700">
            <div className="text-sm text-green-700 dark:text-green-300 mb-2">
              <span className="font-semibold">Progress Preview:</span>
            </div>
            <div className="text-sm text-[hsl(var(--text))]">
              <div className="flex justify-between mb-1">
                <span>Current: {formatCurrency(selectedGoal.current_amount_cents)}</span>
                <span>Target: {formatCurrency(selectedGoal.target_amount_cents)}</span>
              </div>
              <div className="flex justify-between font-semibold">
                <span>After: {formatCurrency(selectedGoal.current_amount_cents + Math.round((parseFloat(amount) || 0) * 100))}</span>
                <span className="text-green-600 dark:text-green-400">{previewProgress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mt-2">
                <div 
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(previewProgress, 100)}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleContribution}
          disabled={!selectedGoalId || !amount || parseFloat(amount) <= 0 || isProcessing}
          className="w-full bg-green-600 hover:bg-green-700 text-white text-lg py-3 font-semibold"
        >
{isProcessing ? (
            'Adding Contribution...'
          ) : (
            <>
              <DollarSign className="h-4 w-4 mr-2" /> Add Contribution
            </>
          )}
        </Button>

        {/* Quick Stats */}
        {selectedGoal && (
          <div className="grid grid-cols-3 gap-2 text-xs text-center mt-4">
            <div className="p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-semibold text-[hsl(var(--text))]">{selectedGoal.progress_percentage.toFixed(1)}%</div>
              <div className="text-[hsl(var(--text))] opacity-60">Complete</div>
            </div>
            <div className="p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-semibold text-[hsl(var(--text))]">{formatCurrency(selectedGoal.remaining_amount)}</div>
              <div className="text-[hsl(var(--text))] opacity-60">Remaining</div>
            </div>
            <div className="p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-semibold text-[hsl(var(--text))]">
                {selectedGoal.target_date ? 
                  goalService.calculateDaysRemaining(selectedGoal.target_date) || '∞' : '∞'} days
              </div>
              <div className="text-[hsl(var(--text))] opacity-60">Left</div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}