import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';

export interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  isLoading?: boolean;
}

export function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'warning',
  isLoading = false
}: ConfirmationModalProps) {
  const handleConfirm = () => {
    onConfirm();
  };

  const getVariantStyles = () => {
    switch (variant) {
      case 'danger':
        return {
          iconColor: 'text-red-500',
          confirmButtonVariant: 'destructive' as const
        };
      case 'warning':
        return {
          iconColor: 'text-yellow-500',
          confirmButtonVariant: 'primary' as const
        };
      case 'info':
        return {
          iconColor: 'text-blue-500',
          confirmButtonVariant: 'primary' as const
        };
      default:
        return {
          iconColor: 'text-yellow-500',
          confirmButtonVariant: 'primary' as const
        };
    }
  };

  const { iconColor, confirmButtonVariant } = getVariantStyles();

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className={`h-6 w-6 ${iconColor}`} />
          <h2 className="text-lg font-semibold text-[hsl(var(--text))]">
            {title}
          </h2>
        </div>
        
        <p className="text-[hsl(var(--text))] opacity-80 mb-6">
          {message}
        </p>
        
        <div className="flex gap-3 justify-end">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            variant={confirmButtonVariant}
            onClick={handleConfirm}
            disabled={isLoading}
            isLoading={isLoading}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}