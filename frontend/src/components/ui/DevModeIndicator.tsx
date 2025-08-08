import React from 'react';
import { mockApiClient } from '../../services/mockApiClient';

interface DevModeIndicatorProps {
  className?: string;
}

export function DevModeIndicator({ className }: DevModeIndicatorProps) {
  const [isVisible, setIsVisible] = React.useState(true);
  const [status, setStatus] = React.useState(mockApiClient.getStatus());

  React.useEffect(() => {
    // Only show in development
    if (import.meta.env.PROD) {
      setIsVisible(false);
      return;
    }

    // Update status periodically
    const interval = setInterval(() => {
      setStatus(mockApiClient.getStatus());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const toggleMockMode = () => {
    if (mockApiClient.isMockMode) {
      mockApiClient.disableMockMode();
    } else {
      mockApiClient.enableMockMode();
    }
    setStatus(mockApiClient.getStatus());
  };

  if (!isVisible) return null;

  const isMockMode = status.useMockData || status.uiOnlyMode;

  return (
    <div className={`fixed top-4 right-4 z-50 ${className}`}>
      <div
        className={`
          px-3 py-2 rounded-lg shadow-lg text-sm font-medium cursor-pointer
          transition-all duration-200 hover:shadow-xl
          ${
            isMockMode
              ? 'bg-yellow-100 text-yellow-800 border-2 border-yellow-300'
              : 'bg-green-100 text-green-800 border-2 border-green-300'
          }
        `}
        onClick={toggleMockMode}
        title="Click to toggle mock mode"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">
            {isMockMode ? '🎭' : '🌐'}
          </span>
          <div className="flex flex-col">
            <span className="font-bold">
              {isMockMode ? 'MOCK MODE' : 'API MODE'}
            </span>
            <span className="text-xs opacity-75">
              {isMockMode
                ? status.uiOnlyMode
                  ? 'UI Only'
                  : 'Mock Data'
                : 'Live API'
              }
              {' • '}{status.mockDelay}ms delay
            </span>
          </div>
        </div>
      </div>

      {/* Debug panel (only visible in dev mode) */}
      {import.meta.env.DEV && (
        <div className="mt-2 p-2 bg-gray-900 text-gray-100 rounded text-xs font-mono">
          <div>Mock: {status.useMockData ? '✅' : '❌'}</div>
          <div>UI Only: {status.uiOnlyMode ? '✅' : '❌'}</div>
          <div>Delay: {status.mockDelay}ms</div>
        </div>
      )}
    </div>
  );
}

// Development console helpers
if (import.meta.env.DEV) {
  (window as unknown as { devMode: Record<string, unknown> }).devMode = {
    enableMock: () => mockApiClient.enableMockMode(),
    disableMock: () => mockApiClient.disableMockMode(),
    setDelay: (ms: number) => mockApiClient.setMockDelay(ms),
    status: () => mockApiClient.getStatus()
  };
  
  console.log('🛠️ Development helpers available at window.devMode');
}