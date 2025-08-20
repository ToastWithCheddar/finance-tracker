import React from 'react';
import { Card, CardContent } from './Card';

export interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon, 
  trend,
  className = ''
}) => (
  <Card className={`${className}`}>
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-[hsl(var(--text))] opacity-70 mb-1">
            {title}
          </p>
          <div className="flex items-baseline space-x-2">
            <p className="text-2xl font-bold text-[hsl(var(--text))]">
              {value}
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
            <p className="text-sm text-[hsl(var(--text))] opacity-60 mt-1">
              {subtitle}
            </p>
          )}
        </div>
        <div className="ml-4">
          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white">
            {icon}
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);