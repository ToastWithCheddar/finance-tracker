import { Component, type ReactNode, type ErrorInfo } from 'react';
import { Button } from '../ui/Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class AsyncErrorBoundary extends Component<Props, State> {
  private retryTimeoutId: number | null = null;

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('AsyncErrorBoundary caught an error:', error, errorInfo);
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to error reporting service in production
    if (import.meta.env.PROD) {
      // TODO: Send to error reporting service (e.g., Sentry)
      console.error('Production error:', { error, errorInfo });
    }
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  handleAutoRetry = () => {
    // Auto-retry after 5 seconds for network errors
    if (this.state.error?.message.includes('fetch') || 
        this.state.error?.message.includes('network') ||
        this.state.error?.message.includes('NetworkError')) {
      
      this.retryTimeoutId = window.setTimeout(() => {
        this.handleRetry();
      }, 5000);
    }
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
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
              <Button onClick={this.handleRetry} variant="outline" size="sm">
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

            {import.meta.env.DEV && (
              <details className="mt-4 text-left">
                <summary className="text-sm text-gray-500 cursor-pointer">
                  Error details (dev only)
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-auto">
                  {this.state.error?.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}