import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  autoRetry?: boolean;
  retryDelay?: number;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  private retryTimeoutId: number | null = null;

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to error reporting service in production
    if (import.meta.env.PROD) {
      // TODO: Send to error reporting service (e.g., Sentry)
      console.error('Production error:', { error, errorInfo });
    }

    // Auto-retry for network errors if enabled
    if (this.props.autoRetry && this.isNetworkError(error)) {
      this.scheduleAutoRetry();
    }
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  handleReset = () => {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
      this.retryTimeoutId = null;
    }
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  private isNetworkError = (error: Error): boolean => {
    return error.message.includes('fetch') || 
           error.message.includes('network') ||
           error.message.includes('NetworkError');
  };

  private scheduleAutoRetry = () => {
    const delay = this.props.retryDelay || 5000;
    this.retryTimeoutId = window.setTimeout(() => {
      this.handleReset();
    }, delay);
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Show compact error UI for network errors or when auto-retry is enabled
      const isNetworkError = this.state.error && this.isNetworkError(this.state.error);
      const showCompactUI = isNetworkError || this.props.autoRetry;

      if (showCompactUI) {
        return (
          <div className="min-h-[200px] flex items-center justify-center p-6">
            <div className="text-center space-y-4 max-w-md">
              <div className="text-red-500 text-xl">⚠️</div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Something went wrong
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>
              
              <div className="flex gap-2 justify-center">
                <Button onClick={this.handleReset} variant="outline" size="sm">
                  Try again
                </Button>
                
                <Button 
                  onClick={() => window.location.reload()} 
                  variant="primary" 
                  size="sm"
                >
                  Reload page
                </Button>
              </div>

              {import.meta.env.DEV && this.state.error && (
                <details className="mt-4 text-left">
                  <summary className="text-sm text-gray-500 cursor-pointer">
                    Error details (dev only)
                  </summary>
                  <pre className="mt-2 text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-auto">
                    {this.state.error.stack}
                  </pre>
                </details>
              )}
            </div>
          </div>
        );
      }

      // Default full-screen error UI for critical errors
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
          <Card className="max-w-lg w-full">
            <div className="p-6 text-center">
              <div className="text-6xl mb-4">⚠️</div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Something went wrong
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
              </p>
              
              {import.meta.env.DEV && this.state.error && (
                <details className="text-left mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <summary className="cursor-pointer font-medium text-red-800 dark:text-red-300 mb-2">
                    Error Details (Development)
                  </summary>
                  <pre className="text-xs text-red-700 dark:text-red-400 overflow-auto">
                    {this.state.error.toString()}
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </details>
              )}
              
              <div className="flex space-x-3 justify-center">
                <Button
                  variant="outline"
                  onClick={() => window.location.reload()}
                >
                  Refresh Page
                </Button>
                <Button
                  onClick={this.handleReset}
                >
                  Try Again
                </Button>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}