import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { goalService } from '../services/goalService';
import { useRealtimeStore } from '../stores/realtimeStore';
import { toast } from 'react-hot-toast';
import type {
  Goal,
  GoalUpdate,
  GoalContributionCreate,
  GoalFilters,
  MilestoneAlert
} from '../types/goals';
import { useEffect } from 'react';
import { queryKeys } from '../services/queryClient';

const goalKeys = queryKeys.goals;

// Query keys
// These are unique identifiers for the goals data in the query cache.
// They are used to invalidate the cache when the data changes.


// Main goals hook
export function useGoals(filters: GoalFilters = {}) {
  const queryClient = useQueryClient();
  const { milestoneAlerts, goalUpdates } = useRealtimeStore();  // TODO: fix this

  const query = useQuery({
    queryKey: goalKeys.list(filters),
    queryFn: () => goalService.getGoals(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Handle real-time updates
  useEffect(() => {
    if (goalUpdates.length > 0) {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: goalKeys.stats() });
    }
  }, [goalUpdates, queryClient]);

  // Handle milestone alerts
  useEffect(() => {
    milestoneAlerts.forEach((alert: MilestoneAlert) => {
      toast.success(alert.celebration_message, {
        duration: 5000,
        icon: '🎉',
      });
    });
  }, [milestoneAlerts]);

  return query;
}

// Individual goal hook
export function useGoal(goalId: string) {
  return useQuery({
    queryKey: goalKeys.detail(goalId),
    queryFn: () => goalService.getGoal(goalId),
    enabled: !!goalId,
  });
}

// Goal statistics hook
export function useGoalStats() {
  return useQuery({
    queryKey: goalKeys.stats(),
    queryFn: goalService.getGoalStats,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Goal type options hook
export function useGoalOptions() {
  return useQuery({
    queryKey: goalKeys.options(),
    queryFn: goalService.getGoalTypeOptions,
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

// Goal contributions hook
export function useGoalContributions(goalId: string, skip = 0, limit = 50) {
  return useQuery({
    queryKey: goalKeys.contributions(goalId),
    queryFn: () => goalService.getGoalContributions(goalId, skip, limit),
    enabled: !!goalId,
  });
}

// Create goal mutation
export function useCreateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: goalService.createGoal,
    onSuccess: (newGoal) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: goalKeys.stats() });
      
      toast.success(`Goal "${newGoal.name}" created successfully! 🎯`, {
        duration: 4000,
      });
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to create goal');
    },
  });
}

// Update goal mutation
export function useUpdateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ goalId, goalData }: { goalId: string; goalData: GoalUpdate }) =>
      goalService.updateGoal(goalId, goalData),
    onSuccess: (updatedGoal) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(updatedGoal.id) });
      queryClient.invalidateQueries({ queryKey: goalKeys.stats() });
      
      if (updatedGoal.status === 'completed') {
        toast.success(`🎊 Congratulations! "${updatedGoal.name}" is now complete!`, {
          duration: 6000,
        });
      } else {
        toast.success('Goal updated successfully');
      }
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to update goal');
    },
  });
}

// Delete goal mutation
export function useDeleteGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: goalService.deleteGoal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: goalKeys.stats() });
      
      toast.success('Goal deleted successfully');
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to delete goal');
    },
  });
}

// Add contribution mutation
export function useAddContribution() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ goalId, contributionData }: { 
      goalId: string; 
      contributionData: GoalContributionCreate 
    }) => goalService.addContribution(goalId, contributionData),
    onSuccess: (contribution, variables) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(variables.goalId) });
      queryClient.invalidateQueries({ queryKey: goalKeys.contributions(variables.goalId) });
      queryClient.invalidateQueries({ queryKey: goalKeys.stats() });
      
      toast.success(`Contribution of $${contribution.amount.toFixed(2)} added! 💰`, {
        duration: 4000,
      });
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to add contribution');
    },
  });
}

// Process automatic contributions mutation
export function useProcessAutoContributions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: goalService.processAutoContributions,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: goalKeys.stats() });
      
      if (result.results.success > 0) {
        toast.success(
          `Processed ${result.results.success} automatic contributions`,
          { duration: 4000 }
        );
      }
      
      if (result.results.failed > 0) {
        toast.error(
          `${result.results.failed} automatic contributions failed`,
          { duration: 4000 }
        );
      }
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      toast.error(error.response?.data?.detail || 'Failed to process automatic contributions');
    },
  });
}

// Custom hook for goal progress animations
export function useGoalProgress(goal: Goal) {
  
  return {
    currentProgress: goal.progress_percentage,
    isCompleted: goal.is_completed,
    remainingAmount: goal.remaining_amount,
    daysRemaining: goalService.calculateDaysRemaining(goal.target_date || ''),
    monthlyRequired: (() => {
      const days = goalService.calculateDaysRemaining(goal.target_date || '');
      return goalService.calculateMonthlyRequired(goal.remaining_amount, days);
    })(),
    progressColor: goal.progress_percentage >= 100 ? 'green' : 
                  goal.progress_percentage >= 75 ? 'blue' :
                  goal.progress_percentage >= 50 ? 'yellow' : 'red',
  };
}

// Custom hook for milestone tracking
export function useMilestoneTracking(goal: Goal) {
  const milestones = [25, 50, 75, 100];
  
  const nextMilestone = milestones.find(m => m > goal.progress_percentage);
  const lastMilestone = milestones.filter(m => m <= goal.progress_percentage).pop() || 0;
  
  return {
    nextMilestone,
    lastMilestone,
    progressToNextMilestone: nextMilestone ? 
      ((goal.progress_percentage - lastMilestone) / (nextMilestone - lastMilestone)) * 100 : 100,
    milestonesReached: goal.milestones?.length || 0,
    celebrationMessage: nextMilestone ? 
      `${(nextMilestone - goal.progress_percentage).toFixed(1)}% to next milestone!` : 
      'Goal completed! 🎉'
  };
}