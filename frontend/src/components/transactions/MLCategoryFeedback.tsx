import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Toast } from '../ui/Toast';

interface MLCategoryFeedbackProps {
  transactionId: string;
  predictedCategory: string;
  actualCategory?: string;
  confidence: number;
  confidenceLevel: string;
  onFeedbackSubmitted?: () => void;
}

interface Category {
  id: string;
  name: string;
}

// Mock categories - in production, this would come from an API
const categories: Category[] = [
  { id: 'food-dining', name: 'Food & Dining' },
  { id: 'transportation', name: 'Transportation' },
  { id: 'shopping', name: 'Shopping' },
  { id: 'bills-utilities', name: 'Bills & Utilities' },
  { id: 'entertainment', name: 'Entertainment' },
  { id: 'healthcare', name: 'Healthcare' },
  { id: 'income', name: 'Income' },
];

export const MLCategoryFeedback: React.FC<MLCategoryFeedbackProps> = ({
  transactionId,
  predictedCategory,
  actualCategory,
  confidence,
  confidenceLevel,
  onFeedbackSubmitted,
}) => {
  const [selectedCategory, setSelectedCategory] = useState(actualCategory || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [showFeedbackForm, setShowFeedbackForm] = useState(!actualCategory);

  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const handleSubmitFeedback = async () => {
    if (!selectedCategory) return;

    setIsSubmitting(true);
    try {
      const response = await fetch('/api/ml/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transaction_id: transactionId,
          predicted_category: predictedCategory,
          actual_category: selectedCategory,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      setToastMessage('Thank you for your feedback! This helps improve our ML model.');
      setShowToast(true);
      setShowFeedbackForm(false);
      onFeedbackSubmitted?.();
    } catch (error) {
      console.error('Error submitting feedback:', error);
      setToastMessage('Failed to submit feedback. Please try again.');
      setShowToast(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isPredictionCorrect = actualCategory && actualCategory === predictedCategory;

  return (
    <>
      <Card className="p-4 border-l-4 border-l-blue-500 bg-blue-50">
        <div className="space-y-3">
          {/* ML Prediction Info */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-gray-900">ML Categorization</h4>
              <p className="text-sm text-gray-600">
                Predicted: <span className="font-medium">{predictedCategory}</span>
              </p>
            </div>
            <div className="text-right">
              <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getConfidenceColor(confidenceLevel)}`}>
                {confidenceLevel.toUpperCase()} ({(confidence * 100).toFixed(1)}%)
              </div>
            </div>
          </div>

          {/* Feedback Status */}
          {actualCategory && (
            <div className={`p-3 rounded ${isPredictionCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center">
                {isPredictionCorrect ? (
                  <div className="text-green-700">
                    ✅ Prediction was correct! Thanks for confirming.
                  </div>
                ) : (
                  <div className="text-red-700">
                    ❌ Prediction was incorrect. Actual: <span className="font-medium">{actualCategory}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Feedback Form */}
          {showFeedbackForm && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Is this categorization correct? If not, please select the right category:
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select correct category...</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex space-x-2">
                <Button
                  onClick={handleSubmitFeedback}
                  disabled={!selectedCategory || isSubmitting}
                  className="flex-1"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowFeedbackForm(false)}
                  disabled={isSubmitting}
                >
                  Skip
                </Button>
              </div>
            </div>
          )}

          {/* Show Feedback Button */}
          {!showFeedbackForm && !actualCategory && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFeedbackForm(true)}
              className="w-full"
            >
              Provide Feedback
            </Button>
          )}
        </div>
      </Card>

      {showToast && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}
    </>
  );
};