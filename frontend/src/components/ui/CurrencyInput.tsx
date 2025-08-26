import { useState, useEffect, forwardRef } from 'react';
import { Input } from './Input';
import type { InputProps } from './Input';

interface CurrencyInputProps extends Omit<InputProps, 'value' | 'onChange' | 'type'> {
  /** Value in cents */
  value?: number;
  /** Callback when value changes, receives cents */
  onChange?: (cents: number) => void;
  /** Currency symbol to display */
  currencySymbol?: string;
  /** Called when input loses focus */
  onBlur?: () => void;
}

/**
 * Enhanced currency input component with smart formatting and validation
 * Based on the Budget form's superior input design
 */
export const CurrencyInput = forwardRef<HTMLInputElement, CurrencyInputProps>(
  ({ value = 0, onChange, onBlur, currencySymbol = '$', className, ...props }, ref) => {
    // Local state for display value (what user sees)
    const [displayValue, setDisplayValue] = useState<string>('');

    // Initialize display value when component mounts or value changes
    useEffect(() => {
      if (value !== undefined) {
        setDisplayValue(formatCurrencyDisplay(value));
      }
    }, [value]);

    // Format cents to display string (e.g., 1234 -> "12.34")
    const formatCurrencyDisplay = (cents: number): string => {
      if (cents === 0) return '';
      return (cents / 100).toFixed(2);
    };

    // Parse display input to cents (e.g., "12.34" -> 1234)
    const parseCurrencyInput = (input: string): number => {
      // Remove any non-numeric characters except decimal point
      const cleaned = input.replace(/[^\d.]/g, '');
      const numericValue = parseFloat(cleaned);
      return isNaN(numericValue) ? 0 : Math.round(numericValue * 100);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const input = e.target.value;
      
      // Allow only digits and a single decimal point with up to 2 decimals
      if (/^\d*(?:\.\d{0,2})?$/.test(input)) {
        setDisplayValue(input);
        const cents = parseCurrencyInput(input);
        onChange?.(cents);
      }
    };

    const handleInputBlur = () => {
      // Format on blur for better UX
      const cents = parseCurrencyInput(displayValue);
      const formatted = cents > 0 ? formatCurrencyDisplay(cents) : '';
      setDisplayValue(formatted);
      onChange?.(cents);
      onBlur?.();
    };

    return (
      <div className="relative">
        <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 pointer-events-none">
          {currencySymbol}
        </span>
        <Input
          ref={ref}
          type="text"
          inputMode="decimal"
          pattern="^\d*\.?\d{0,2}$"
          value={displayValue}
          onChange={handleInputChange}
          onBlur={handleInputBlur}
          className={`pl-8 ${className || ''}`}
          placeholder="0.00"
          {...props}
        />
      </div>
    );
  }
);

CurrencyInput.displayName = 'CurrencyInput';