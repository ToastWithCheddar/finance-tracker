import React, { useState } from 'react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { GoalCard } from '../components/goals/GoalCard';
import { GoalForm } from '../components/goals/GoalForm';
import { GoalsDashboard } from '../components/goals/GoalDashboard';
import { useGoals, useDeleteGoal, useProcessAutoContributions } from '../hooks/useGoals';
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
  const processAutoContributions = useProcessAutoContributions();

  const handleDeleteGoal = async (goalId: string) => {
    if (window.confirm('Are you sure you want to delete this goal? This action cannot be undone.')) {
      try {
        await deleteGoal.mutateAsync(goalId);
      } catch {
        // Error handling is done in the hook
      }
    }
  };

  const handleProcessAutoContributions = async () => {
    if (window.confirm('Process automatic contributions for all eligible goals?')) {
      try {
        await processAutoContributions.mutateAsync();
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
        <Card className="p-8 text-center">
          <div className="text-red-500 text-xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to Load Goals</h2>
          <p className="text-gray-600 mb-4">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <Button onClick={() => window.location.reload()}>
            Try Again
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Financial Goals</h1>
          <p className="text-gray-600">
            Track your progress and achieve your financial dreams
          </p>
        </div>
        
        <div className="flex items-center space-x-3 mt-4 lg:mt-0">
          <Button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            ➕ Create Goal
          </Button>
          
          <Button
            onClick={handleProcessAutoContributions}
            variant="outline"
            disabled={processAutoContributions.isPending}
          >
            {processAutoContributions.isPending ? 'Processing...' : '🔄 Auto Contributions'}
          </Button>
        </div>
      </div>

      {/* View Mode Selector */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">View:</span>
          <div className="flex rounded-lg border border-gray-200 p-1">
            <button
              onClick={() => setViewMode('dashboard')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'dashboard' 
                  ? 'bg-blue-500 text-white' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'list' 
                  ? 'bg-blue-500 text-white' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              📋 List
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === 'grid' 
                  ? 'bg-blue-500 text-white' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              🔲 Grid
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-3">
          <select
            value={filters.status || ''}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as GoalStatus || undefined }))}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                  {goalsData.overall_progress.toFixed(1)}%
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
            <Card className="p-12 text-center">
              <div className="text-6xl mb-4">🎯</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No Goals Found</h3>
              <p className="text-gray-600 mb-6">
                {Object.values(filters).some(f => f) 
                  ? "No goals match your current filters. Try adjusting them or clearing all filters."
                  : "Start your financial journey by creating your first goal!"
                }
              </p>
              {!Object.values(filters).some(f => f) && (
                <Button
                  onClick={() => setShowCreateForm(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Create Your First Goal
                </Button>
              )}
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