import React from 'react';

interface EmptyStateProps {
  icon?: React.ReactNode | string;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  className?: string;
}

export function EmptyState({ 
  icon, 
  title, 
  description, 
  action,
  className = ''
}: EmptyStateProps) {
  const renderIcon = () => {
    if (!icon) return null;
    
    if (typeof icon === 'string') {
      return <div className="text-6xl mb-4">{icon}</div>;
    }
    
    return React.isValidElement(icon) ? 
      <div className="mb-4">{icon}</div> : 
      <div className="text-6xl mb-4">{icon}</div>;
  };

  return (
    <div className={`text-center py-12 ${className}`}>
      {renderIcon()}
      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
        {title}
      </h3>
      <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
        {description}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          className={`inline-flex items-center px-4 py-2 border text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 ${
            action.variant === 'secondary'
              ? 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-gray-500'
              : 'border-transparent text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
          }`}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}