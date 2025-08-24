interface ErrorStateProps {
  message?: string;
  error?: Error | unknown;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function ErrorState({ 
  message, 
  error, 
  onRetry, 
  retryLabel = 'Try Again',
  className = ''
}: ErrorStateProps) {
  const errorMessage = message || 
    (error instanceof Error ? error.message : 'An unexpected error occurred');

  return (
    <div className={`flex items-center justify-center py-12 ${className}`}>
      <div className="text-center max-w-md">
        <div className="text-red-500 text-4xl mb-4">⚠️</div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Something went wrong
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {errorMessage}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            {retryLabel}
          </button>
        )}
      </div>
    </div>
  );
}