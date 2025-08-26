import React, { useState } from 'react';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { GoalCard } from '../components/goals/GoalCard';
import { GoalForm } from '../components/goals/GoalForm';
import { GoalsDashboard } from '../components/goals/GoalDashboard';
import { useGoals, useDeleteGoal } from '../hooks/useGoals';
import { GoalStatus, GoalType, GoalPriority, type Goal } from '../types/goals';
import { toast } from 'react-hot-toast';

type ViewMode = 'dashboard' | 'list' | 'grid';

export default function Goals() {
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [filters, setFilters] = useState({
    status: undefined as GoalStatus | undefined,
    goal_type: undefined as GoalType | undefined,
    priority: undefined as GoalPriority | undefined,
  });

  const { data: goalsData, isLoading, error } = useGoals(filters);
  const deleteGoal = useDeleteGoal();

  const handleDeleteGoal = async (goalId: string) => {
    if (window.confirm('Are you sure you want to delete this goal? This action cannot be undone.')) {
      try {
        await deleteGoal.mutateAsync(goalId);
      } catch {
        // Error handling is done in the hook
      }
    }
  };


  const handleEditGoal = (goal: Goal) => {
    setEditingGoal(goal);
  };

  const handleCloseForm = () => {
    setShowCreateForm(false);
    setEditingGoal(null);
  };

  const clearFilters = () => {
    setFilters({
      status: undefined,
      goal_type: undefined,
      priority: undefined,
    });
  };

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <ErrorState
          error={error}
          message="Failed to Load Goals"
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-[hsl(var(--text))] mb-2">Financial Goals</h1>
          <p className="text-[hsl(var(--text))] opacity-70">
            Track your progress and achieve your financial dreams
          </p>
        </div>
        
        <div className="flex items-center space-x-3 mt-4 lg:mt-0">
          <Button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Create Goal
          </Button>
          
        </div>
      </div>

      {/* View Mode Selector */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-[hsl(var(--text))] opacity-80">View:</span>
          <div className="flex rounded-lg border border-[hsl(var(--border))] p-1">
            <button
              onClick={() => setViewMode('dashboard')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'dashboard' 
                  ? 'bg-[hsl(var(--brand))] text-white' 
                  : 'text-[hsl(var(--text))] opacity-70 hover:opacity-100'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'list' 
                  ? 'bg-[hsl(var(--brand))] text-white' 
                  : 'text-[hsl(var(--text))] opacity-70 hover:opacity-100'
              }`}
            >
              📋 List
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'grid' 
                  ? 'bg-[hsl(var(--brand))] text-white' 
                  : 'text-[hsl(var(--text))] opacity-70 hover:opacity-100'
              }`}
            >
              🔲 Grid
            </button>
          </div>
        </div>

        {/* Filters - Only show for list and grid views */}
        {viewMode !== 'dashboard' && (
          <div className="flex items-center space-x-3">
            <select
              value={filters.status || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as GoalStatus || undefined }))}
              className="px-3 py-1 text-sm rounded-md focus:outline-none focus:ring-2 bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))] focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))]"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="paused">Paused</option>
              <option value="cancelled">Cancelled</option>
            </select>
            
            <select
              value={filters.goal_type || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, goal_type: e.target.value as GoalType || undefined }))}
              className="px-3 py-1 text-sm rounded-md focus:outline-none focus:ring-2 bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))] focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))]"
            >
              <option value="">All Types</option>
              <option value="savings">Savings</option>
              <option value="debt_payoff">Debt Payoff</option>
              <option value="emergency_fund">Emergency Fund</option>
              <option value="investment">Investment</option>
              <option value="purchase">Purchase</option>
              <option value="other">Other</option>
            </select>
            
            <select
              value={filters.priority || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, priority: e.target.value as GoalPriority || undefined }))}
              className="px-3 py-1 text-sm rounded-md focus:outline-none focus:ring-2 bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))] focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))]"
            >
              <option value="">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            
            {(filters.status || filters.goal_type || filters.priority) && (
              <Button onClick={clearFilters} variant="outline" size="sm">
                Clear
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : viewMode === 'dashboard' ? (
        <GoalsDashboard />
      ) : (
        <div>
          {/* Quick Stats */}
          {goalsData && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <Card className="p-4 text-center">
                <div className="text-2xl font-bold text-blue-600">{goalsData.active_goals}</div>
                <div className="text-sm text-gray-600">Active Goals</div>
              </Card>
              <Card className="p-4 text-center">
                <div className="text-2xl font-bold text-green-600">{goalsData.completed_goals}</div>
                <div className="text-sm text-gray-600">Completed</div>
              </Card>
              <Card className="p-4 text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {Number(
                    goalsData.overall_progress ?? (
                      goalsData.total_target_amount_cents
                        ? (goalsData.total_current_amount_cents / goalsData.total_target_amount_cents) * 100
                        : 0
                    )
                  ).toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">Overall Progress</div>
              </Card>
              <Card className="p-4 text-center">
                <div className="text-2xl font-bold text-orange-600">{goalsData.total}</div>
                <div className="text-sm text-gray-600">Total Goals</div>
              </Card>
            </div>
          )}

          {/* Goals List/Grid */}
          {goalsData?.goals && goalsData.goals.length > 0 ? (
            <div className={
              viewMode === 'grid' 
                ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
                : "space-y-6"
            }>
              {goalsData.goals.map((goal) => (
                <GoalCard
                  key={goal.id}
                  goal={goal}
                  onEdit={handleEditGoal}
                  onDelete={handleDeleteGoal}
                  compact={viewMode === 'grid'}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent>
                <EmptyState
                  icon="🎯"
                  title="No Goals Found"
                  description={Object.values(filters).some(f => f) 
                    ? "No goals match your current filters. Try adjusting them or clearing all filters."
                    : "Start your financial journey by creating your first goal!"
                  }
                  action={!Object.values(filters).some(f => f) ? {
                    label: 'Create Your First Goal',
                    onClick: () => setShowCreateForm(true)
                  } : undefined}
                />
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Goal Form Modal */}
      <GoalForm
        goal={editingGoal || undefined}
        isOpen={showCreateForm || !!editingGoal}
        onClose={handleCloseForm}
        onSuccess={() => {
          handleCloseForm();
          toast.success(editingGoal ? 'Goal updated successfully!' : 'Goal created successfully!');
        }}
      />
    </div>
  );
}
