import React from 'react';
import { Toaster, toast } from 'sonner';

// -----------------------------------------------------------------------------
// Toast Provider using sonner (FE-LOG-002 — replaced react-hot-toast).
// -----------------------------------------------------------------------------
export interface ToastProviderProps {
  children: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  return (
    <>
      {children}
      <Toaster position="bottom-right" richColors closeButton />
    </>
  );
}

// Convenience hooks for different toast types — sonner-compatible signatures.
export const useToast = () => toast;
export const useSuccessToast = () => (message: string) => toast.success(message);
export const useErrorToast = () => (message: string) => toast.error(message);
export const useWarningToast = () => (message: string) => toast.warning(message);
export const useInfoToast = () => (message: string) => toast.info(message);

// Toast types for compatibility
export type ToastType = 'success' | 'error' | 'warning' | 'info';
