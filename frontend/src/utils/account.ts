/**
 * Account-related utility functions for consistent account handling
 * across components
 */

import {
  Banknote,
  CreditCard,
  PiggyBank,
  TrendingUp,
  Wallet,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Wifi,
  Clock
} from 'lucide-react';

/**
 * Get the appropriate icon component for an account type
 */
export function getAccountIcon(accountType: string | undefined | null, withColors = false) {
  const type = accountType?.toLowerCase() || 'unknown';
  
  switch (type) {
    case 'checking':
      return withColors ? 
        <Banknote className="h-5 w-5 text-blue-600" /> :
        <Banknote className="h-5 w-5" />;
    
    case 'savings':
      return withColors ?
        <PiggyBank className="h-5 w-5 text-green-600" /> :
        <Banknote className="h-5 w-5" />;
    
    case 'credit':
    case 'credit_card':
      return withColors ?
        <CreditCard className="h-5 w-5 text-red-600" /> :
        <CreditCard className="h-5 w-5" />;
    
    case 'investment':
      return withColors ?
        <TrendingUp className="h-5 w-5 text-purple-600" /> :
        <TrendingUp className="h-5 w-5" />;
    
    default:
      return withColors ?
        <Wallet className="h-5 w-5 text-gray-600" /> :
        <Banknote className="h-5 w-5" />;
  }
}

/**
 * Get the CSS classes for health status styling
 */
export function getHealthColor(health: string | undefined | null): string {
  switch (health) {
    case 'healthy':
      return 'text-green-600 bg-green-100';
    case 'warning':
      return 'text-yellow-600 bg-yellow-100';
    case 'failed':
      return 'text-red-600 bg-red-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

/**
 * Get human-readable label for account type
 */
export function getAccountTypeLabel(accountType: string | undefined | null): string {
  const type = accountType?.toLowerCase() || 'unknown';
  
  switch (type) {
    case 'checking':
      return 'Checking';
    case 'savings':
      return 'Savings';
    case 'credit_card':
      return 'Credit Card';
    case 'investment':
      return 'Investment';
    default:
      return 'Unknown';
  }
}

/**
 * Get human-readable label for connection health
 */
export function getConnectionHealthLabel(health: string | undefined | null): string {
  switch (health) {
    case 'healthy':
      return 'Healthy';
    case 'warning':
      return 'Warning';
    case 'failed':
      return 'Failed';
    default:
      return 'Unknown';
  }
}

/**
 * Get CSS color classes for connection health text
 */
export function getConnectionHealthColor(health: string | undefined | null): string {
  switch (health) {
    case 'healthy':
      return 'text-green-600';
    case 'warning':
      return 'text-yellow-600';
    case 'failed':
      return 'text-red-600';
    default:
      return 'text-gray-500';
  }
}

/**
 * Get status icon for connection health status
 */
export function getConnectionStatusIcon(status: string) {
  switch (status) {
    case 'healthy':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'warning':
      return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-500" />;
    default:
      return <Wifi className="h-5 w-5 text-gray-400" />;
  }
}

/**
 * Get status text for connection health status
 */
export function getConnectionStatusText(status: string): string {
  switch (status) {
    case 'healthy':
      return 'Connected';
    case 'warning':
      return 'Sync Overdue';
    case 'failed':
      return 'Connection Failed';
    default:
      return 'Unknown';
  }
}

/**
 * Get CSS classes for connection status styling (badge style)
 */
export function getConnectionStatusColor(status: string): string {
  switch (status) {
    case 'healthy':
      return 'text-green-600 bg-green-50';
    case 'warning':
      return 'text-yellow-600 bg-yellow-50';
    case 'failed':
      return 'text-red-600 bg-red-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
}

/**
 * Get reconciliation status icon based on reconciliation state and discrepancy
 */
export function getReconciliationStatusIcon(isReconciled: boolean, discrepancy: number) {
  if (isReconciled) {
    return <CheckCircle className="h-6 w-6 text-green-500" />;
  } else if (Math.abs(discrepancy) < 10) {
    return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
  } else {
    return <XCircle className="h-6 w-6 text-red-500" />;
  }
}

/**
 * Get CSS classes for reconciliation status styling (border and background)
 */
export function getReconciliationStatusColor(isReconciled: boolean, discrepancy: number): string {
  if (isReconciled) {
    return 'text-green-600 bg-green-50 border-green-200';
  } else if (Math.abs(discrepancy) < 10) {
    return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  } else {
    return 'text-red-600 bg-red-50 border-red-200';
  }
}

/**
 * Get health status icon for account connections
 */
export function getHealthIcon(health?: string) {
  switch (health) {
    case 'healthy':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'warning':
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    case 'failed':
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
}