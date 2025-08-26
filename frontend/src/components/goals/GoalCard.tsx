import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { DollarSign, Trophy, Pause, Play, Edit, Trash2, Sparkles } from 'lucide-react';
import { useAddContribution, useUpdateGoal, useGoalProgress, useMilestoneTracking } from '../../hooks/useGoals';
import { useAccounts } from '../../hooks/useAccounts';
import { goalService } from '../../services/goalService';
import { formatCurrency } from '../../utils/currency';
import { getRelativeTime } from '../../utils/date';
import type { Goal, GoalContributionCreate, GoalUpdate, GoalStatus } from '../../types/goals';
import { GoalStatus as GoalStatusConst } from '../../types/goals';

interface GoalCardProps {
  goal: Goal;
  onEdit?: (goal: Goal) => void;
  onDelete?: (goalId: string) => void;
  compact?: boolean;
}

export function GoalCard({ goal, onEdit, onDelete, compact = false }: GoalCardProps) {
  const [showContributionModal, setShowContributionModal] = useState(false);
  const [contributionAmount, setContributionAmount] = useState('');
  const [contributionNote, setContributionNote] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const addContribution = useAddContribution();
  const updateGoal = useUpdateGoal();
  const { data: accounts } = useAccounts();
  const { currentProgress, isCompleted, remainingAmount, daysRemaining, monthlyRequired, progressColor } = useGoalProgress(goal);
  const { nextMilestone, progressToNextMilestone } = useMilestoneTracking(goal);

  const typeInfo = goalService.getGoalTypeInfo(goal.goal_type);
  const priorityInfo = goalService.getPriorityInfo(goal.priority);
  const statusInfo = goalService.getStatusInfo(goal.status);

  const handleContribution = async () => {
    if (!contributionAmount || parseFloat(contributionAmount) <= 0) return;

    setIsProcessing(true);
    try {
      const contributionData: GoalContributionCreate = {
        amount_cents: Math.round(parseFloat(contributionAmount) * 100),
        note: contributionNote || undefined,
      };

      await addContribution.mutateAsync({
        goalId: goal.id,
        contributionData,
      });

      setContributionAmount('');
      setContributionNote('');
      setShowContributionModal(false);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStatusChange = async (newStatus: GoalStatus) => {
    const updateData: GoalUpdate = { status: newStatus };
    await updateGoal.mutateAsync({
      goalId: goal.id,
      goalData: updateData,
    });
  };

  const getProgressBarColor = () => {
    switch (progressColor) {
      case 'green': return 'bg-green-500';
      case 'blue': return 'bg-blue-500';
      case 'yellow': return 'bg-yellow-500';
      case 'red': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getPriorityBadgeColor = () => {
    switch (priorityInfo.color) {
      case 'red': return 'bg-red-100 text-red-800 border-red-200';
      case 'orange': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'blue': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (compact) {
    return (
      <Card className="p-4 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <typeInfo.icon className="h-5 w-5 text-blue-500" />
            <h3 className="font-semibold text-lg truncate text-[hsl(var(--text))]">{goal.name}</h3>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs border ${getPriorityBadgeColor()}`}>
            {priorityInfo.label}
          </span>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-[hsl(var(--text))] opacity-80">
            <span>{formatCurrency(goal.current_amount_cents)}</span>
            <span>{formatCurrency(goal.target_amount_cents)}</span>
          </div>
          
          <div className="w-full rounded-full h-2 bg-[hsl(var(--border))]">
            <div
              className={`${getProgressBarColor()} h-2 rounded-full transition-all duration-500 ease-out`}
              style={{ width: `${Math.min(currentProgress, 100)}%` }}
            />
          </div>
          
          <div className="flex justify-between text-xs text-[hsl(var(--text))] opacity-70">
            <span>{currentProgress.toFixed(1)}% complete</span>
            {daysRemaining && <span>{daysRemaining} days left</span>}
          </div>
          
          {/* Quick Contribution Button for Compact Cards */}
          {goal.status === GoalStatusConst.ACTIVE && !isCompleted && (
            <div className="flex justify-center mt-3">
              <Button
                onClick={() => setShowContributionModal(true)}
                size="sm"
                className="bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1"
              >
<DollarSign className="h-3 w-3 mr-1" /> Add $
              </Button>
            </div>
          )}
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className="p-6 hover:shadow-lg transition-all duration-200 border-l-4 border-l-blue-500">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/20">
              <typeInfo.icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[hsl(var(--text))]">{goal.name}</h3>
              {goal.description && (
                <p className="text-[hsl(var(--text))] opacity-80 text-sm mt-1">{goal.description}</p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 rounded-full text-sm border ${getPriorityBadgeColor()}`}>
              {priorityInfo.label}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm bg-${statusInfo.color}-100 text-${statusInfo.color}-800 flex items-center space-x-1`}>
              <statusInfo.icon className="h-3 w-3" />
              <span>{statusInfo.label}</span>
            </span>
          </div>
        </div>

        {/* Progress Section */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-2xl font-bold text-[hsl(var(--text))]">
              {formatCurrency(goal.current_amount_cents)}
            </span>
            <span className="text-lg text-[hsl(var(--text))] opacity-70">
              of {formatCurrency(goal.target_amount_cents)}
            </span>
          </div>
          
          <div className="relative">
            <div className="w-full rounded-full h-4 mb-2 bg-[hsl(var(--border))]">
              <div
                className={`${getProgressBarColor()} h-4 rounded-full transition-all duration-1000 ease-out relative overflow-hidden`}
                style={{ width: `${Math.min(currentProgress, 100)}%` }}
              >
                {/* Animated shine effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white via-transparent opacity-30 animate-pulse" />
              </div>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="font-semibold text-[hsl(var(--text))]">
                {currentProgress.toFixed(1)}% Complete
              </span>
              {!isCompleted && (
                <span className="text-[hsl(var(--text))] opacity-70">
                  {formatCurrency(remainingAmount)} remaining
                </span>
              )}
            </div>
          </div>

          {/* Milestone Progress */}
          {nextMilestone && !isCompleted && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <div className="flex justify-between text-sm text-blue-700 mb-1">
                <span>Next milestone: {nextMilestone}%</span>
                <span>{progressToNextMilestone.toFixed(1)}% there</span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progressToNextMilestone}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Goal Details */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 text-sm">
          {goal.target_date && (
            <div className="p-3 rounded-lg bg-[hsl(var(--surface))] border border-[hsl(var(--border))]">
              <span className="block text-[hsl(var(--text))] opacity-60">Target Date</span>
              <span className="font-semibold">
                {new Date(goal.target_date).toLocaleDateString()}
              </span>
              {daysRemaining !== null && (
                <div className="text-xs text-[hsl(var(--text))] opacity-70 mt-1">
                  {daysRemaining > 0 ? `${daysRemaining} days left` : 'Overdue'}
                </div>
              )}
            </div>
          )}
          
          {monthlyRequired && (
            <div className="p-3 rounded-lg bg-[hsl(var(--surface))] border border-[hsl(var(--border))]">
              <span className="block text-[hsl(var(--text))] opacity-60">Monthly Target</span>
              <span className="font-semibold">
                {formatCurrency(monthlyRequired)}
              </span>
              <div className="text-xs text-[hsl(var(--text))] opacity-70 mt-1">to reach goal</div>
            </div>
          )}
          
          {goal.last_contribution_date && (
            <div className="p-3 rounded-lg bg-[hsl(var(--surface))] border border-[hsl(var(--border))]">
              <span className="block text-[hsl(var(--text))] opacity-60">Last Contribution</span>
              <span className="font-semibold">
                {getRelativeTime(goal.last_contribution_date)}
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          {goal.status === GoalStatusConst.ACTIVE && !isCompleted && (
            <>
              <Button
                onClick={() => setShowContributionModal(true)}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
<DollarSign className="h-4 w-4 mr-2" /> Add Contribution
              </Button>
              
              {isCompleted && (
                <Button
                  onClick={() => handleStatusChange(GoalStatusConst.COMPLETED)}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
<Trophy className="h-4 w-4 mr-2" /> Mark Complete
                </Button>
              )}
            </>
          )}
          
          {goal.status === GoalStatusConst.ACTIVE && (
            <Button
              onClick={() => handleStatusChange(GoalStatusConst.PAUSED)}
              variant="outline"
            >
<Pause className="h-4 w-4 mr-2" /> Pause
            </Button>
          )}
          
          {goal.status === GoalStatusConst.PAUSED && (
            <Button
              onClick={() => handleStatusChange(GoalStatusConst.ACTIVE)}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
<Play className="h-4 w-4 mr-2" /> Resume
            </Button>
          )}
          
          {onEdit && (
            <Button onClick={() => onEdit(goal)} variant="outline">
              <Edit className="h-4 w-4 mr-2" /> Edit
            </Button>
          )}
          
          {onDelete && goal.status !== GoalStatusConst.COMPLETED && (
            <Button
              onClick={() => onDelete(goal.id)}
              variant="outline"
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
<Trash2 className="h-4 w-4 mr-2" /> Delete
            </Button>
          )}
        </div>

        {/* Celebration Message */}
        {isCompleted && (
          <div className="mt-4 p-4 bg-success-gradient rounded-lg border border-green-200 dark:border-green-700">
            <div className="text-center">
              <div className="mb-2 flex justify-center">
                <Sparkles className="h-8 w-8 text-green-600 dark:text-green-300" />
              </div>
              <p className="font-semibold text-green-800 dark:text-green-100">
                Congratulations! You've achieved your goal!
              </p>
              <p className="text-sm text-green-700 dark:text-green-200 mt-1">
                Final amount: {formatCurrency(goal.current_amount_cents)}
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Contribution Modal */}
      <Modal
        isOpen={showContributionModal}
        onClose={() => setShowContributionModal(false)}
        title={`Add Contribution to ${goal.name}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contribution Amount
            </label>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={contributionAmount}
              onChange={(e) => setContributionAmount(e.target.value)}
              placeholder="Enter amount"
              className="w-full"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Note (optional)
            </label>
            <Input
              value={contributionNote}
              onChange={(e) => setContributionNote(e.target.value)}
              placeholder="Add a note about this contribution"
              className="w-full"
            />
          </div>
          
          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-sm text-blue-700">
              <span className="font-semibold">Progress after contribution:</span><br />
              {formatCurrency(goal.current_amount_cents + Math.round((parseFloat(contributionAmount) || 0) * 100))} of {formatCurrency(goal.target_amount_cents)}
              {' '}({Math.min(((goal.current_amount_cents + Math.round((parseFloat(contributionAmount) || 0) * 100)) / goal.target_amount_cents * 100), 100).toFixed(1)}%)
            </p>
          </div>
          
          <div className="flex space-x-3 pt-4">
            <Button
              onClick={handleContribution}
              disabled={!contributionAmount || parseFloat(contributionAmount) <= 0 || isProcessing}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white"
            >
              {isProcessing ? 'Adding...' : 'Add Contribution'}
            </Button>
            <Button
              onClick={() => setShowContributionModal(false)}
              variant="outline"
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
