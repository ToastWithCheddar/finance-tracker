import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';

export type MetricCardTheme = 'default' | 'income' | 'expense' | 'success' | 'savings';

interface ThemeStyles {
  cardClass: string;
  iconColor: string;
  titleColor: string;
  valueColor: string;
  changeColor: string;
}

// Single source of truth for the five theme variants. A color tweak now
// changes one row, not six branches (FE-PR-006 / phase A3).
const THEME_STYLES: Record<MetricCardTheme, ThemeStyles> = {
  income: {
    cardClass: 'bg-income-gradient border-income-200 shadow-lg shadow-income-100/50 dark:shadow-income-800/50',
    iconColor: 'text-income-600 dark:text-green-300',
    titleColor: 'text-income-700 dark:text-gray-300',
    valueColor: 'text-income-900 dark:text-gray-100',
    changeColor: 'text-income-600 dark:text-gray-400',
  },
  expense: {
    cardClass: 'bg-expense-gradient border-expense-200 shadow-lg shadow-expense-100/50 dark:shadow-expense-800/50',
    iconColor: 'text-expense-600 dark:text-red-300',
    titleColor: 'text-expense-700 dark:text-gray-300',
    valueColor: 'text-expense-900 dark:text-gray-100',
    changeColor: 'text-expense-600 dark:text-gray-400',
  },
  success: {
    cardClass: 'bg-success-gradient border-success-200 shadow-lg shadow-success-100/50 dark:shadow-success-800/50',
    iconColor: 'text-success-600 dark:text-green-300',
    titleColor: 'text-success-700 dark:text-gray-300',
    valueColor: 'text-success-900 dark:text-gray-100',
    changeColor: 'text-success-600 dark:text-gray-400',
  },
  savings: {
    cardClass: 'bg-savings-gradient border-savings-200 shadow-lg shadow-savings-100/50 dark:shadow-savings-800/50',
    iconColor: 'text-savings-600 dark:text-blue-300',
    titleColor: 'text-savings-700 dark:text-gray-300',
    valueColor: 'text-savings-900 dark:text-gray-100',
    changeColor: 'text-savings-600 dark:text-gray-400',
  },
  default: {
    cardClass: 'bg-gradient-to-br from-white to-gray-50 border-gray-200 shadow-lg dark:from-gray-800 dark:to-gray-700 dark:border-gray-600',
    iconColor: 'text-gray-500 dark:text-gray-400',
    titleColor: 'text-gray-600 dark:text-gray-400',
    valueColor: 'text-gray-900 dark:text-gray-100',
    changeColor: 'text-gray-600 dark:text-gray-400',
  },
};

// Override applied when caller passes `change + changeType` without a
// theme — flips the card to success/expense based on the change sign.
function deriveChangeOverride(changeType: 'positive' | 'negative' | 'neutral'): ThemeStyles {
  const isPositive = changeType === 'positive';
  return isPositive
    ? {
        cardClass: 'bg-success-gradient border-success-200 dark:border-success-700 shadow-lg shadow-success-100/50 dark:shadow-success-800/50',
        iconColor: 'text-success-600 dark:text-success-300',
        titleColor: 'text-success-700 dark:text-success-200',
        valueColor: 'text-success-900 dark:text-success-100',
        changeColor: 'text-success-600 dark:text-success-300',
      }
    : {
        cardClass: 'bg-expense-gradient border-expense-200 dark:border-expense-700 shadow-lg shadow-expense-100/50 dark:shadow-expense-800/50',
        iconColor: 'text-expense-600 dark:text-expense-300',
        titleColor: 'text-expense-700 dark:text-expense-200',
        valueColor: 'text-expense-900 dark:text-expense-100',
        changeColor: 'text-expense-600 dark:text-expense-300',
      };
}

export interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: React.ReactNode;
  iconComponent?: React.ComponentType<{ className?: string; size?: number | string; }>;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  theme?: MetricCardTheme;
  isLoading?: boolean;
  isUpdating?: boolean;
  className?: string;
  variant?: 'compact' | 'standard';
}

export const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon,
  iconComponent: IconComponent,
  trend,
  change,
  changeType = 'neutral',
  theme = 'default',
  isLoading = false,
  isUpdating = false,
  className = '',
  variant = 'standard'
}) => {
  // Single lookup; if change-driven override applies, swap once.
  const cardTheme: ThemeStyles =
    change && changeType !== 'neutral' && theme === 'default'
      ? deriveChangeOverride(changeType)
      : THEME_STYLES[theme];

  const ChangeIcon = changeType === 'positive' ? TrendingUp : TrendingDown;

  if (variant === 'compact') {
    return (
      <Card className={`
        ${cardTheme.cardClass}
        card-hover
        transition-all duration-300 
        ${isUpdating ? 'ring-2 ring-blue-300 scale-105 glow-savings animate-bounce-gentle' : ''}
        backdrop-blur-sm
        ${className}
      `}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className={`text-sm font-medium ${cardTheme.titleColor}`}>
            {title}
          </CardTitle>
          <div className="relative">
            {IconComponent && (
              <>
                <IconComponent className={`h-5 w-5 ${cardTheme.iconColor} ${isUpdating ? 'animate-pulse' : ''}`} />
                {isUpdating && (
                  <div className="absolute inset-0 animate-ping">
                    <IconComponent className={`h-5 w-5 ${cardTheme.iconColor} opacity-75`} />
                  </div>
                )}
              </>
            )}
            {icon && !IconComponent && (
              <div className={`${cardTheme.iconColor} ${isUpdating ? 'animate-pulse' : ''}`}>
                {icon}
                {isUpdating && (
                  <div className="absolute inset-0 animate-ping opacity-75">
                    {icon}
                  </div>
                )}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className={`
            text-3xl font-bold transition-all duration-300 
            ${cardTheme.valueColor}
            ${isLoading ? 'animate-pulse shimmer' : ''}
          `}>
            {isLoading ? '...' : value}
          </div>
          {change && (
            <div className={`flex items-center text-sm ${cardTheme.changeColor} mt-2 font-medium`}>
              <ChangeIcon className="h-4 w-4 mr-1" />
              {change}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // Standard variant (original design)
  return (
    <Card className={`${className} ${cardTheme.cardClass}`}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className={`text-sm font-medium ${cardTheme.titleColor} mb-1`}>
              {title}
            </p>
            <div className="flex items-baseline space-x-2">
              <p className={`text-2xl font-bold ${cardTheme.valueColor} ${isLoading ? 'animate-pulse shimmer' : ''}`}>
                {isLoading ? '...' : value}
              </p>
              {trend && (
                <span className={`text-xs px-2 py-1 rounded-full ${
                  trend.isPositive 
                    ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                    : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                }`}>
                  {trend.isPositive ? '+' : ''}{trend.value}% {trend.label}
                </span>
              )}
            </div>
            {subtitle && (
              <p className={`text-sm ${cardTheme.titleColor} opacity-60 mt-1`}>
                {subtitle}
              </p>
            )}
          </div>
          <div className="ml-4">
            <div className="w-12 h-12 rounded-lg bg-button-primary-gradient flex items-center justify-center text-white">
              {IconComponent && <IconComponent className="h-6 w-6" />}
              {icon && !IconComponent && icon}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};