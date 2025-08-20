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
