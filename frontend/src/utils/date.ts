/**
 * Date and time utility functions for consistent date handling
 * across components
 */

/**
 * Format a timestamp to show relative time for sync status
 */
export function formatLastSync(lastSync: string | null): string {
  if (!lastSync) return 'Never';
  
  const syncDate = new Date(lastSync);
  const now = new Date();
  const diffHours = Math.floor((now.getTime() - syncDate.getTime()) / (1000 * 60 * 60));
  
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffHours < 168) return `${Math.floor(diffHours / 24)}d ago`;
  return syncDate.toLocaleDateString();
}

/**
 * Format a date for display in reconciliation context
 */
export function formatReconciliationDate(date: string): string {
  return new Date(date).toLocaleDateString();
}

/**
 * Get relative time string (e.g., "2 hours ago", "yesterday")
 */
export function getRelativeTime(date: string | Date): string {
  const targetDate = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - targetDate.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) === 1 ? '' : 's'} ago`;
  
  return targetDate.toLocaleDateString();
}

/**
 * Check if a date is today
 */
export function isToday(date: string | Date): boolean {
  const targetDate = new Date(date);
  const today = new Date();
  
  return targetDate.toDateString() === today.toDateString();
}

/**
 * Format date for form inputs (YYYY-MM-DD)
 */
export function formatDateForInput(date: string | Date): string {
  const targetDate = new Date(date);
  return targetDate.toISOString().split('T')[0];
}

/**
 * Parse date string safely, returning null if invalid
 */
export function parseDate(dateStr: string): Date | null {
  const date = new Date(dateStr);
  return isNaN(date.getTime()) ? null : date;
}