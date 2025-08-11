import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface AlertProps {
  variant?: 'default' | 'destructive' | 'warning' | 'success';
  className?: string;
  children: ReactNode;
}

interface AlertTitleProps {
  className?: string;
  children: ReactNode;
}

interface AlertDescriptionProps {
  className?: string;
  children: ReactNode;
}

export function Alert({ variant = 'default', className, children }: AlertProps) {
  return (
    <div
      className={clsx(
        'relative w-full rounded-lg border p-4',
        {
          'border-gray-200 bg-white text-gray-900': variant === 'default',
          'border-red-200 bg-red-50 text-red-900': variant === 'destructive',
          'border-yellow-200 bg-yellow-50 text-yellow-900': variant === 'warning',
          'border-green-200 bg-green-50 text-green-900': variant === 'success',
        },
        className
      )}
      role="alert"
    >
      {children}
    </div>
  );
}

export function AlertTitle({ className, children }: AlertTitleProps) {
  return (
    <h5 className={clsx('mb-1 font-medium leading-none tracking-tight', className)}>
      {children}
    </h5>
  );
}

export function AlertDescription({ className, children }: AlertDescriptionProps) {
  return (
    <div className={clsx('text-sm [&_p]:leading-relaxed', className)}>
      {children}
    </div>
  );
}