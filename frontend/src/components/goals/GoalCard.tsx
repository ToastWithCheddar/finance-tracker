import { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { useAddContribution, useUpdateGoal, useGoalProgress, useMilestoneTracking } from '../../hooks/useGoals';
import { goalService } from '../../services/goalService';
import { formatCurrency, formatRelativeTime } from '../../utils';
import type { Goal, GoalContributionCreate, GoalUpdate, GoalStatus } from '../../types/goals';

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

  const handleStatusChange = async (newStatus: string) => {
    const updateData: GoalUpdate = { status: newStatus as GoalStatus };
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
            <span className="text-xl">{typeInfo.icon}</span>
            <h3 className="font-semibold text-lg truncate">{goal.name}</h3>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs border ${getPriorityBadgeColor()}`}>
            {priorityInfo.label}
          </span>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>{formatCurrency(goal.current_amount_cents)}</span>
            <span>{formatCurrency(goal.target_amount_cents)}</span>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`${getProgressBarColor()} h-2 rounded-full transition-all duration-500 ease-out`}
              style={{ width: `${Math.min(currentProgress, 100)}%` }}
            />
          </div>
          
          <div className="flex justify-between text-xs text-gray-500">
            <span>{currentProgress.toFixed(1)}% complete</span>
            {daysRemaining && <span>{daysRemaining} days left</span>}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className="p-6 hover:shadow-lg transition-all duration-200 border-l-4 border-l-blue-500">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="text-3xl">{typeInfo.icon}</div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">{goal.name}</h3>
              {goal.description && (
                <p className="text-gray-600 text-sm mt-1">{goal.description}</p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 rounded-full text-sm border ${getPriorityBadgeColor()}`}>
              {priorityInfo.label}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm bg-${statusInfo.color}-100 text-${statusInfo.color}-800`}>
              {statusInfo.icon} {statusInfo.label}
            </span>
          </div>
        </div>

        {/* Progress Section */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-2xl font-bold text-gray-900">
              {formatCurrency(goal.current_amount_cents)}
            </span>
            <span className="text-lg text-gray-600">
              of {formatCurrency(goal.target_amount_cents)}
            </span>
          </div>
          
          <div className="relative">
            <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
              <div
                className={`${getProgressBarColor()} h-4 rounded-full transition-all duration-1000 ease-out relative overflow-hidden`}
                style={{ width: `${Math.min(currentProgress, 100)}%` }}
              >
                {/* Animated shine effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white via-transparent opacity-30 animate-pulse" />
              </div>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="font-semibold text-gray-700">
                {currentProgress.toFixed(1)}% Complete
              </span>
              {!isCompleted && (
                <span className="text-gray-600">
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
            <div className="bg-gray-50 p-3 rounded-lg">
              <span className="text-gray-500 block">Target Date</span>
              <span className="font-semibold">
                {new Date(goal.target_date).toLocaleDateString()}
              </span>
              {daysRemaining !== null && (
                <div className="text-xs text-gray-600 mt-1">
                  {daysRemaining > 0 ? `${daysRemaining} days left` : 'Overdue'}
                </div>
              )}
            </div>
          )}
          
          {monthlyRequired && (
            <div className="bg-gray-50 p-3 rounded-lg">
              <span className="text-gray-500 block">Monthly Target</span>
              <span className="font-semibold">
                {formatCurrency(monthlyRequired)}
              </span>
              <div className="text-xs text-gray-600 mt-1">to reach goal</div>
            </div>
          )}
          
          {goal.last_contribution_date && (
            <div className="bg-gray-50 p-3 rounded-lg">
              <span className="text-gray-500 block">Last Contribution</span>
              <span className="font-semibold">
                {formatRelativeTime(goal.last_contribution_date)}
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          {goal.status === 'active' && !isCompleted && (
            <>
              <Button
                onClick={() => setShowContributionModal(true)}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                💰 Add Contribution
              </Button>
              
              {isCompleted && (
                <Button
                  onClick={() => handleStatusChange('completed')}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  🎉 Mark Complete
                </Button>
              )}
            </>
          )}
          
          {goal.status === 'active' && (
            <Button
              onClick={() => handleStatusChange('paused')}
              variant="outline"
            >
              ⏸️ Pause
            </Button>
          )}
          
          {goal.status === 'paused' && (
            <Button
              onClick={() => handleStatusChange('active')}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              ▶️ Resume
            </Button>
          )}
          
          {onEdit && (
            <Button onClick={() => onEdit(goal)} variant="outline">
              ✏️ Edit
            </Button>
          )}
          
          {onDelete && goal.status !== 'completed' && (
            <Button
              onClick={() => onDelete(goal.id)}
              variant="outline"
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              🗑️ Delete
            </Button>
          )}
        </div>

        {/* Celebration Message */}
        {isCompleted && (
          <div className="mt-4 p-4 bg-gradient-to-r from-green-100 to-blue-100 rounded-lg border border-green-200">
            <div className="text-center">
              <div className="text-2xl mb-2">🎊</div>
              <p className="font-semibold text-green-800">
                Congratulations! You've achieved your goal!
              </p>
              <p className="text-sm text-green-700 mt-1">
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