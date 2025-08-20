import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { useToast } from '../ui/Toast';
import { apiClient } from '../../services/api';
import { categoryService } from '../../services/categoryService';
import type { Category } from '../../types/category';

interface MLCategoryFeedbackProps {
  transactionId: string;
  predictedCategory: string;
  actualCategory?: string;
  confidence: number;
  confidenceLevel: string;
  onFeedbackSubmitted?: () => void;
}


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
  const [showFeedbackForm, setShowFeedbackForm] = useState(!actualCategory);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const toast = useToast();

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const fetchedCategories = await categoryService.getMyCategories();
        setCategories(fetchedCategories);
      } catch (error) {
        console.error('Error loading categories:', error);
        toast.error('Failed to load categories');
      } finally {
        setIsLoadingCategories(false);
      }
    };

    loadCategories();
  }, [toast]);

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
      await apiClient.post('/ml/feedback', {
        transaction_id: transactionId,
        predicted_category: predictedCategory,
        actual_category: selectedCategory,
      });

      toast.success('Thank you for your feedback! This helps improve our ML model.');
      setShowFeedbackForm(false);
      onFeedbackSubmitted?.();
    } catch (error) {
      console.error('Error submitting feedback:', error);
      toast.error('Failed to submit feedback. Please try again.');
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
                  disabled={isLoadingCategories}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                >
                  <option value="">
                    {isLoadingCategories ? 'Loading categories...' : 'Select correct category...'}
                  </option>
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
                  disabled={!selectedCategory || isSubmitting || isLoadingCategories}
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
    </>
  );
};