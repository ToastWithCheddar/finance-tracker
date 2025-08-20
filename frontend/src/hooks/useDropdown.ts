import { useEffect, useState, useRef } from 'react';

interface UseDropdownOptions {
  /** CSS class selector for the dropdown container (e.g., '.my-dropdown') */
  containerSelector: string;
  /** Whether to close the dropdown when clicking outside (default: true) */
  closeOnOutsideClick?: boolean;
  /** Whether to close the dropdown when pressing Escape (default: true) */
  closeOnEscape?: boolean;
  /** Callback function called when the dropdown opens */
  onOpen?: () => void;
  /** Callback function called when the dropdown closes */
  onClose?: () => void;
}

interface UseDropdownReturn {
  /** Whether the dropdown is currently open */
  isOpen: boolean;
  /** Function to open the dropdown */
  open: () => void;
  /** Function to close the dropdown */
  close: () => void;
  /** Function to toggle the dropdown state */
  toggle: () => void;
  /** Ref to attach to the trigger element for focus management */
  triggerRef: React.RefObject<HTMLElement>;
}

/**
 * A reusable hook for managing dropdown state and behavior with consistent
 * outside-click detection, escape key handling, and focus management.
 */
export function useDropdown(options: UseDropdownOptions): UseDropdownReturn {
  const {
    containerSelector,
    closeOnOutsideClick = true,
    closeOnEscape = true,
    onOpen,
    onClose,
  } = options;

  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const open = () => {
    if (!isOpen) {
      // Store the current active element for later restoration
      previousActiveElement.current = document.activeElement as HTMLElement;
      setIsOpen(true);
      onOpen?.();
    }
  };

  const close = () => {
    if (isOpen) {
      setIsOpen(false);
      onClose?.();
      
      // Restore focus to the trigger element or previously active element
      if (triggerRef.current) {
        triggerRef.current.focus();
      } else if (previousActiveElement.current) {
        previousActiveElement.current.focus();
      }
    }
  };

  const toggle = () => {
    if (isOpen) {
      close();
    } else {
      open();
    }
  };

  // Handle outside clicks
  useEffect(() => {
    if (!closeOnOutsideClick || !isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest(containerSelector)) {
        close();
      }
    };

    // Use a small delay to avoid immediate closure on the same click that opened it
    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, containerSelector, closeOnOutsideClick]);

  // Handle escape key
  useEffect(() => {
    if (!closeOnEscape || !isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, closeOnEscape]);

  return {
    isOpen,
    open,
    close,
    toggle,
    triggerRef,
  };
}