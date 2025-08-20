import React from 'react';
import { apiClient } from '../../services/api';

interface DevModeIndicatorProps {
  className?: string;
}

export function DevModeIndicator({ className }: DevModeIndicatorProps) {
  const [isVisible, setIsVisible] = React.useState(true);
  const [apiStatus, setApiStatus] = React.useState<'connected' | 'disconnected' | 'checking'>('checking');

  React.useEffect(() => {
    // Only show in development
    if (import.meta.env.PROD) {
      setIsVisible(false);
      return;
    }

    // Check API connectivity periodically
    const checkApiStatus = async () => {
      try {
        // Try a simple health check or endpoint
        await apiClient.get('/health');
        setApiStatus('connected');
      } catch {
        setApiStatus('disconnected');
      }
    };

    checkApiStatus();
    const interval = setInterval(checkApiStatus, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

  if (!isVisible) return null;

  const statusConfig = {
    connected: {
      icon: '🌐',
      label: 'API CONNECTED',
      detail: 'Live Backend',
      className: 'bg-green-100 text-green-800 border-2 border-green-300'
    },
    disconnected: {
      icon: '🔴',
      label: 'API DISCONNECTED', 
      detail: 'Backend Offline',
      className: 'bg-red-100 text-red-800 border-2 border-red-300'
    },
    checking: {
      icon: '🔄',
      label: 'CHECKING API',
      detail: 'Connecting...',
      className: 'bg-yellow-100 text-yellow-800 border-2 border-yellow-300'
    }
  };

  const config = statusConfig[apiStatus];

  return (
    <div className={`fixed top-4 right-4 z-50 ${className}`}>
      <div
        className={`
          px-3 py-2 rounded-lg shadow-lg text-sm font-medium
          transition-all duration-200
          ${config.className}
        `}
        title="API Connection Status"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <div className="flex flex-col">
            <span className="font-bold">{config.label}</span>
            <span className="text-xs opacity-75">{config.detail}</span>
          </div>
        </div>
      </div>

      {/* Debug panel (only visible in dev mode) */}
      {import.meta.env.DEV && (
        <div className="mt-2 p-2 bg-gray-900 text-gray-100 rounded text-xs font-mono">
          <div>Status: {apiStatus}</div>
          <div>Backend: {import.meta.env.VITE_API_URL}</div>
          <div>Environment: {import.meta.env.MODE}</div>
        </div>
      )}
    </div>
  );
}

// Development console helpers
if (import.meta.env.DEV) {
  (window as unknown as { devMode: Record<string, unknown> }).devMode = {
    checkApi: () => apiClient.get('/health'),
    getApiUrl: () => import.meta.env.VITE_API_URL
  };
  
  console.log('🛠️ Development helpers available at window.devMode');
}