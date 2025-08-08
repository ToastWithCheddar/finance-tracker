import React from 'react';
import { Toaster, toast } from 'react-hot-toast';

// -----------------------------------------------------------------------------
// Toast Provider using react-hot-toast
// -----------------------------------------------------------------------------
export interface ToastProviderProps {
  children: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#4ade80',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </>
  );
}

// Convenience hooks for different toast types
export const useToast = () => toast;
export const useSuccessToast = () => (message: string) => toast.success(message);
export const useErrorToast = () => (message: string) => toast.error(message);
export const useWarningToast = () => (message: string) => toast(message, { icon: '⚠️' });
export const useInfoToast = () => (message: string) => toast(message, { icon: 'ℹ️' });

// Toast types for compatibility
export type ToastType = 'success' | 'error' | 'warning' | 'info';

// -----------------------------------------------------------------------------
// Inline toast component for simple ad-hoc usage (e.g., MLModelDashboard)  
// -----------------------------------------------------------------------------
export interface ToastProps {
  message: string;
  type: ToastType;
  onClose?: () => void;
}

export function Toast({ message, type, onClose }: ToastProps) {
  const bg = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    warning: 'bg-yellow-600',
    info: 'bg-blue-600'
  }[type];

  return (
    <div className={`fixed bottom-4 right-4 px-4 py-3 rounded shadow-lg text-white ${bg}`}> 
      <div className="flex items-center space-x-2">
        <span>{message}</span>
        {onClose && (
          <button onClick={onClose} className="ml-2 text-white hover:opacity-75">✖</button>
        )}
      </div>
    </div>
  );
}
