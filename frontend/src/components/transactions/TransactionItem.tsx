import { useState } from 'react';
import type { Transaction } from '../../types/transaction';
import { Card, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { mlService } from '../../services/mlService';

import { formatCurrency } from '../../utils/currency';
import { formatDate } from '../../utils/date';
import { getTransactionStatusVisuals } from '../../utils';
import { ChevronDown, Pencil, Trash2, Building, Tag, FileText, Calendar, CreditCard, Check, Clock, CheckCheck, Circle, Brain, ThumbsUp, ThumbsDown } from 'lucide-react';

interface TransactionItemProps {
  transaction: Transaction;
  onEdit: (transaction: Transaction) => void;
  onDelete: (transactionId: string) => void;
  showCheckbox?: boolean;
  isSelected?: boolean;
  onSelect?: (transactionId: string) => void;
}

export function TransactionItem({ 
  transaction, 
  onEdit, 
  onDelete,
  showCheckbox = false,
  isSelected = false,
  onSelect
}: TransactionItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const handleMLFeedback = async (isHelpful: boolean) => {
    const categoryName = transaction.categoryName || transaction.category_name;
    if (!transaction.description || !categoryName) return;
    
    try {
      if (isHelpful) {
        // Thumbs up: reinforce the current categorization
        const trainingText = transaction.merchant 
          ? `${transaction.merchant} ${transaction.description}` 
          : transaction.description;
        
        await mlService.addCategoryExample({
          category: categoryName,
          example: trainingText
        });
        
      } else {
        // Thumbs down: User disagrees with categorization
        
        alert('Thanks for the feedback! In the future, this will let you pick the correct category to improve AI accuracy.');
      }
    } catch (error) {
      console.error('Failed to submit ML feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    }
  };

  const isIncome = transaction.amountCents > 0;
  const amountColor = isIncome ? 'text-green-600' : 'text-gray-900 dark:text-gray-100';
  

  // Get status visuals
  const statusVisuals = transaction.status ? getTransactionStatusVisuals(transaction.status) : null;
  
  // Map icon names to actual icon components
  const getStatusIcon = (iconName: string) => {
    const iconMap = { Clock, Check, CheckCheck, Circle };
    const IconComponent = iconMap[iconName as keyof typeof iconMap];
    return IconComponent ? <IconComponent className="h-3 w-3" /> : <Circle className="h-3 w-3" />;
  };

  const formatAccountInfo = () => {
    const name = transaction.accountName || 'Unknown Account';
    const type = transaction.accountType;
    return type ? `${name} (${type})` : name;
  };

  const getMLConfidenceBadge = () => {
    const confidence = transaction.confidenceScore || transaction.confidence_score;
    if (!confidence) return null;

    let level: string;
    let colorClass: string;
    
    if (confidence >= 0.8) {
      level = 'High';
      colorClass = 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
    } else if (confidence >= 0.5) {
      level = 'Med';
      colorClass = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
    } else {
      level = 'Low';
      colorClass = 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
    }

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${colorClass}`}>
        <Brain className="h-3 w-3" />
        {level}
      </span>
    );
  };


  return (
    <Card className="hover:shadow-md transition-shadow duration-200">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          {/* Left Side: Checkbox, Icon, Description, Date */}
          <div className="flex items-center space-x-4 flex-1 min-w-0">
            {showCheckbox && onSelect && (
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onSelect(transaction.id)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            )}
            
            <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
              isIncome ? 'bg-green-100 dark:bg-green-900/20' : 'bg-gray-100 dark:bg-gray-800'
            }`}>
              {transaction.categoryEmoji || transaction.category_emoji ? (
                <span className="text-xl">
                  {transaction.categoryEmoji || transaction.category_emoji}
                </span>
              ) : (
                <span className="text-gray-400 dark:text-gray-500">
                  {isIncome ? '💰' : '💳'}
                </span>
              )}
            </div>
            
            <div className="min-w-0 flex-1">
              <div className="flex flex-col">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 min-w-0 flex-1">
                    <p className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {transaction.merchant || transaction.description || 'No description'}
                    </p>
                    {statusVisuals && (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${statusVisuals.colorClass}`}>
                        {getStatusIcon(statusVisuals.iconName)}
                        {statusVisuals.label}
                      </span>
                    )}
                    {getMLConfidenceBadge()}
                  </div>
                  {/* Prominent Date Display */}
                  <div className="flex items-center text-sm font-medium text-gray-600 dark:text-gray-300 ml-2">
                    <Calendar className="h-4 w-4 mr-1" />
                    {formatDate(transaction.transactionDate, { month: 'short', day: 'numeric' })}
                  </div>
                </div>
                {transaction.merchant && transaction.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                    {transaction.description}
                  </p>
                )}
                {!transaction.merchant && !transaction.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                    No description available
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Right Side: Amount and Actions */}
          <div className="flex items-center space-x-4">
            <p className={`font-bold text-lg ${amountColor}`}>
              {isIncome ? '+' : '-'}{formatCurrency(Math.abs(transaction.amountCents))}
            </p>
            <div className="flex items-center space-x-1">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => onEdit(transaction)} 
                aria-label="Edit transaction"
                className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20"
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => onDelete(transaction.id)} 
                aria-label="Delete transaction"
                className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setIsExpanded(!isExpanded)} 
                aria-label={isExpanded ? "Collapse details" : "Expand details"}
                className="text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <ChevronDown className={`h-5 w-5 transition-transform duration-200 ${
                  isExpanded ? 'rotate-180' : ''
                }`} />
              </Button>
            </div>
          </div>
        </div>
        
        {/* Expandable Content */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3 animate-in slide-in-from-top-2 duration-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Account Information */}
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <CreditCard className="h-4 w-4 mr-2 text-gray-400 dark:text-gray-500" />
                <strong className="mr-2">Account:</strong>
                <span className="truncate">{formatAccountInfo()}</span>
              </div>

              {/* Transaction Date */}
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <Calendar className="h-4 w-4 mr-2 text-gray-400 dark:text-gray-500" />
                <strong className="mr-2">Date:</strong>
                <span>{formatDate(transaction.transactionDate, { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric',
                  weekday: 'short'
                })}</span>
              </div>

              {/* Transaction Status */}
              {transaction.status && (
                <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                  {getStatusIcon(statusVisuals?.iconName || 'Circle')}
                  <strong className="ml-2 mr-2">Status:</strong>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusVisuals?.colorClass || 'bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200'}`}>
                    {statusVisuals?.label || transaction.status}
                  </span>
                </div>
              )}

              {/* Currency */}
              <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                <strong className="mr-2">Currency:</strong>
                <span>{transaction.currency || 'USD'}</span>
              </div>
            </div>

            {/* Notes */}
            {transaction.notes && (
              <div className="flex items-start text-sm text-gray-600 dark:text-gray-400">
                <FileText className="h-4 w-4 mr-2 mt-0.5 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                <div>
                  <strong className="mr-2">Notes:</strong>
                  <span className="break-words">{transaction.notes}</span>
                </div>
              </div>
            )}

            {/* Tags */}
            {transaction.tags && transaction.tags.length > 0 && (
              <div className="flex items-start text-sm text-gray-600 dark:text-gray-400">
                <Tag className="h-4 w-4 mr-2 mt-0.5 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                <div>
                  <strong className="mr-2">Tags:</strong>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {transaction.tags.map((tag, index) => (
                      <span 
                        key={index} 
                        className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Location */}
            {transaction.location && (
              <div className="flex items-start text-sm text-gray-600 dark:text-gray-400">
                <Building className="h-4 w-4 mr-2 mt-0.5 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                <div>
                  <strong className="mr-2">Location:</strong>
                  <span className="break-words">{transaction.location.address}</span>
                </div>
              </div>
            )}

            {/* Recurring Information removed */}

            {/* ML Confidence Score */}
            {transaction.confidenceScore !== undefined && (
              <div className="space-y-2">
                <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                  <strong className="mr-2">ML Confidence:</strong>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    transaction.confidenceScore >= 0.8 
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
                      : transaction.confidenceScore >= 0.6
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200'
                      : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
                  }`}>
                    {Math.round(transaction.confidenceScore * 100)}%
                  </span>
                </div>
                
                {/* ML Feedback Buttons */}
                {transaction.mlSuggestedCategoryId && (
                  <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                    <strong className="mr-2">Was this categorization helpful?</strong>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMLFeedback(true)}
                        className="text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20 px-2 py-1"
                      >
                        <ThumbsUp className="h-3 w-3 mr-1" />
                        Yes
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMLFeedback(false)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 px-2 py-1"
                      >
                        <ThumbsDown className="h-3 w-3 mr-1" />
                        No
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Plaid Transaction ID for debugging */}
            {transaction.plaidTransactionId && (
              <div className="flex items-center text-xs text-gray-500 dark:text-gray-500">
                <strong className="mr-2">Plaid ID:</strong>
                <span className="font-mono truncate">{transaction.plaidTransactionId}</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
