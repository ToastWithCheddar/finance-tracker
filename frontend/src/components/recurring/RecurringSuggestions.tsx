import React from 'react';
import { CheckCircle, X, Calendar, TrendingUp, DollarSign } from 'lucide-react';
import type { RecurringSuggestion } from '../../types/recurring';
import { useApproveSuggestion, useDismissSuggestion } from '../../hooks/useRecurring';
import { Button } from '../ui/Button';
import { formatCurrency } from '../../utils/currency';

interface RecurringSuggestionsProps {
  suggestions: RecurringSuggestion[];
}

export const RecurringSuggestions: React.FC<RecurringSuggestionsProps> = ({ suggestions }) => {
  const approveSuggestion = useApproveSuggestion();
  const dismissSuggestion = useDismissSuggestion();

  const handleApprove = (suggestion: RecurringSuggestion) => {
    approveSuggestion.mutate({
      suggestion_id: suggestion.id,
    });
  };

  const handleDismiss = (suggestion: RecurringSuggestion) => {
    dismissSuggestion.mutate(suggestion.id);
  };

  const getFrequencyDisplay = (frequency: string, interval: number) => {
    const freqMap: Record<string, string> = {
      weekly: 'Week',
      biweekly: '2 Weeks',
      monthly: 'Month',
      quarterly: '3 Months',
      annually: 'Year',
    };

    const baseFreq = freqMap[frequency] || frequency;
    return interval === 1 ? `Every ${baseFreq}` : `Every ${interval} ${baseFreq}s`;
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-100';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {suggestions.map((suggestion) => (
        <div
          key={suggestion.id}
          className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-[hsl(var(--surface))] border-[hsl(var(--border))]"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <h3 className="font-semibold text-[hsl(var(--text))]">
                    {suggestion.merchant}
                  </h3>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${getConfidenceColor(
                      suggestion.confidence_score
                    )}`}
                  >
                    {Math.round(suggestion.confidence_score * 100)}% confidence
                  </span>
                </div>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {/* Amount */}
                <div className="flex items-center space-x-2">
                  <DollarSign className="h-4 w-4 text-green-600 dark:text-green-300" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">
                      {formatCurrency(suggestion.amount_dollars)}
                    </div>
                    <div className="text-xs text-[hsl(var(--text))] opacity-70">
                      ±{formatCurrency(suggestion.amount_variation.std_dev_cents / 100)} std dev
                    </div>
                  </div>
                </div>

                {/* Frequency */}
                <div className="flex items-center space-x-2">
                  <Calendar className="h-4 w-4 text-blue-600 dark:text-blue-300" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">
                      {getFrequencyDisplay(suggestion.frequency, suggestion.interval)}
                    </div>
                    <div className="text-xs text-[hsl(var(--text))] opacity-70">
                      Next expected: {formatDate(suggestion.next_expected_date)}
                    </div>
                  </div>
                </div>

                {/* Transaction Count */}
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-purple-600 dark:text-purple-300" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">
                      {suggestion.transaction_count} transactions
                    </div>
                    <div className="text-xs text-[hsl(var(--text))] opacity-70">
                      Detected via {suggestion.detection_method}
                    </div>
                  </div>
                </div>
              </div>

              {/* Sample Dates */}
              <div className="mb-4">
                <div className="text-sm text-[hsl(var(--text))] opacity-70 mb-2">Recent transactions:</div>
                <div className="flex flex-wrap gap-2">
                  {suggestion.sample_dates.slice(-5).map((date, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 text-xs rounded bg-[hsl(var(--border))] text-[hsl(var(--text))]"
                    >
                      {formatDate(date)}
                    </span>
                  ))}
                </div>
              </div>

              {/* Amount Range */}
              <div className="text-sm text-[hsl(var(--text))] opacity-80">
                Amount range: {formatCurrency(suggestion.amount_variation.min_cents / 100)} - {formatCurrency(suggestion.amount_variation.max_cents / 100)}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col space-y-2 ml-4">
              <Button
                onClick={() => handleApprove(suggestion)}
                disabled={approveSuggestion.isPending}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2"
                size="sm"
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Approve
              </Button>
              
              <Button
                onClick={() => handleDismiss(suggestion)}
                disabled={dismissSuggestion.isPending}
                variant="outline"
                size="sm"
                className="text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-200"
              >
                <X className="h-4 w-4 mr-1" />
                Dismiss
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};