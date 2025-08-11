import { useEffect, useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { useRealtimeStore } from '../../stores/realtimeStore';
import { formatCurrency } from '../../utils';
import type { MilestoneAlert } from '../../types/goals';

interface CelebrationModalProps {
  alert: MilestoneAlert;
  isOpen: boolean;
  onClose: () => void;
}

function CelebrationModal({ alert, isOpen, onClose }: CelebrationModalProps) {
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setShowConfetti(true);
      const timer = setTimeout(() => setShowConfetti(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="relative max-w-md w-full mx-4">
        {/* Confetti Animation */}
        {showConfetti && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="absolute animate-bounce"
                style={{
                  left: `${Math.random() * 100}%`,
                  animationDelay: `${Math.random() * 2}s`,
                  animationDuration: `${2 + Math.random() * 2}s`
                }}
              >
                {['🎉', '🎊', '⭐', '🌟', '✨'][Math.floor(Math.random() * 5)]}
              </div>
            ))}
          </div>
        )}

        <Card className="p-8 text-center relative bg-gradient-to-br from-yellow-50 to-orange-50 border-2 border-yellow-200">
          <div className="text-6xl mb-4 animate-pulse">🎊</div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Milestone Achieved!
          </h2>
          
          <p className="text-lg text-gray-700 mb-4">
            {alert.celebration_message}
          </p>
          
          <div className="bg-white bg-opacity-60 rounded-lg p-4 mb-6">
            <div className="text-3xl font-bold text-green-600 mb-1">
              {alert.milestone_percentage}%
            </div>
            <div className="text-sm text-gray-600">
              {formatCurrency(alert.amount_reached_cents)} reached
            </div>
          </div>
          
          <div className="flex justify-center space-x-4">
            <Button
              onClick={onClose}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"
            >
              🎉 Awesome!
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

interface GoalCompletionModalProps {
  goalName: string;
  finalAmount: number;
  isOpen: boolean;
  onClose: () => void;
}

function GoalCompletionModal({ goalName, finalAmount, isOpen, onClose }: GoalCompletionModalProps) {
  const [showFireworks, setShowFireworks] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setShowFireworks(true);
      const timer = setTimeout(() => setShowFireworks(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60">
      <div className="relative max-w-lg w-full mx-4">
        {/* Fireworks Animation */}
        {showFireworks && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {[...Array(30)].map((_, i) => (
              <div
                key={i}
                className="absolute text-2xl animate-ping"
                style={{
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                  animationDelay: `${Math.random() * 3}s`,
                  animationDuration: `${1 + Math.random()}s`
                }}
              >
                {['🎆', '🎇', '✨', '🌟', '💫'][Math.floor(Math.random() * 5)]}
              </div>
            ))}
          </div>
        )}

        <Card className="p-10 text-center relative bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 border-4 border-green-300">
          <div className="text-8xl mb-6 animate-bounce">🏆</div>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Goal Completed!
          </h1>
          
          <p className="text-xl text-gray-700 mb-2">
            Congratulations on achieving
          </p>
          <p className="text-2xl font-bold text-blue-600 mb-4">
            "{goalName}"
          </p>
          
          <div className="bg-white bg-opacity-80 rounded-xl p-6 mb-8">
            <div className="text-4xl font-bold text-green-600 mb-2">
              {formatCurrency(finalAmount)}
            </div>
            <div className="text-lg text-gray-600">
              Final Amount Achieved
            </div>
          </div>
          
          <div className="space-y-4">
            <p className="text-lg text-gray-700">
              🎉 You've successfully reached your financial goal! This is a huge achievement that shows your dedication and smart financial planning.
            </p>
            
            <div className="flex justify-center space-x-4">
              <Button
                onClick={onClose}
                className="bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 text-white px-8 py-3 text-lg"
              >
                🎊 Celebrate!
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export function MilestoneNotifications() {
  const { milestoneAlerts, goalCompletions, clearMilestoneAlert, clearGoalCompletion } = useRealtimeStore();
  const [currentMilestone, setCurrentMilestone] = useState<MilestoneAlert | null>(null);
  const [currentCompletion, setCurrentCompletion] = useState<{ goal_id: string; goal_name: string; final_amount?: number } | null>(null);

  // Handle milestone alerts
  useEffect(() => {
    if (milestoneAlerts.length > 0 && !currentMilestone) {
      const alert = milestoneAlerts[0];
      setCurrentMilestone(alert);
    }
  }, [milestoneAlerts, currentMilestone]);

  // Handle goal completions
  useEffect(() => {
    if (goalCompletions.length > 0 && !currentCompletion) {
      const completion = goalCompletions[0];
      setCurrentCompletion(completion);
    }
  }, [goalCompletions, currentCompletion]);

  const handleCloseMilestone = () => {
    if (currentMilestone) {
      clearMilestoneAlert(currentMilestone.goal_id);
      setCurrentMilestone(null);
      
      // Show next milestone if any
      const remaining = milestoneAlerts.filter(a => a.goal_id !== currentMilestone.goal_id);
      if (remaining.length > 0) {
        setTimeout(() => setCurrentMilestone(remaining[0]), 500);
      }
    }
  };

  const handleCloseCompletion = () => {
    if (currentCompletion) {
      clearGoalCompletion(currentCompletion.goal_id);
      setCurrentCompletion(null);
      
      // Show next completion if any
      const remaining = goalCompletions.filter(c => c.goal_id !== currentCompletion.goal_id);
      if (remaining.length > 0) {
        setTimeout(() => setCurrentCompletion(remaining[0]), 500);
      }
    }
  };

  return (
    <>
      {/* Milestone Achievement Modal */}
      <CelebrationModal
        alert={currentMilestone!}
        isOpen={!!currentMilestone}
        onClose={handleCloseMilestone}
      />

      {/* Goal Completion Modal */}
      <GoalCompletionModal
        goalName={currentCompletion?.goal_name || ''}
        finalAmount={currentCompletion?.final_amount || 0}
        isOpen={!!currentCompletion}
        onClose={handleCloseCompletion}
      />
    </>
  );
}

// Small notification component for subtle milestone updates
export function MilestoneNotificationBadge() {
  const { milestoneAlerts, goalCompletions } = useRealtimeStore();
  const totalNotifications = milestoneAlerts.length + goalCompletions.length;

  if (totalNotifications === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-40">
      <Card className="p-3 bg-gradient-to-r from-green-500 to-blue-500 text-white shadow-lg">
        <div className="flex items-center space-x-2">
          <div className="text-xl animate-bounce">🎉</div>
          <div>
            <div className="font-semibold text-sm">
              {totalNotifications} Achievement{totalNotifications > 1 ? 's' : ''}!
            </div>
            <div className="text-xs opacity-90">
              Click to view celebrations
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// Progress animation component
export function ProgressAnimation({ 
  currentProgress, 
  previousProgress, 
  goalName 
}: { 
  currentProgress: number; 
  previousProgress: number; 
  goalName: string;
}) {
  const [showAnimation, setShowAnimation] = useState(false);
  const [animationProgress, setAnimationProgress] = useState(previousProgress);

  useEffect(() => {
    if (currentProgress > previousProgress) {
      setShowAnimation(true);
      
      // Animate progress bar
      const duration = 1500; // 1.5 seconds
      const steps = 60;
      const increment = (currentProgress - previousProgress) / steps;
      
      let step = 0;
      const timer = setInterval(() => {
        step++;
        setAnimationProgress(prev => Math.min(prev + increment, currentProgress));
        
        if (step >= steps) {
          clearInterval(timer);
          setTimeout(() => setShowAnimation(false), 1000);
        }
      }, duration / steps);

      return () => clearInterval(timer);
    }
  }, [currentProgress, previousProgress]);

  if (!showAnimation) return null;

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <Card className="p-4 bg-white shadow-lg border-l-4 border-l-green-500 max-w-sm">
        <div className="flex items-center space-x-3">
          <div className="text-2xl animate-pulse">📈</div>
          <div className="flex-1">
            <div className="font-semibold text-sm text-gray-900 mb-1">
              Progress Update: {goalName}
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
              <div
                className="bg-green-500 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(animationProgress, 100)}%` }}
              />
            </div>
            
            <div className="text-xs text-gray-600">
              {animationProgress.toFixed(1)}% complete
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}