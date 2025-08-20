/**
 * Utility functions for working with recurring transaction frequencies
 */

/**
 * Format frequency and interval into a human-readable display string
 * @param frequency - The frequency type (weekly, monthly, etc.)
 * @param interval - The interval number (1, 2, 3, etc.)
 * @returns Formatted string like "Every Month" or "Every 2 Weeks"
 */
export function getFrequencyDisplay(frequency: string, interval: number): string {
  const freqMap: Record<string, string> = {
    weekly: 'Week',
    biweekly: '2 Weeks',
    monthly: 'Month',
    quarterly: '3 Months',
    annually: 'Year',
  };

  const baseFreq = freqMap[frequency] || frequency;
  return interval === 1 ? `Every ${baseFreq}` : `Every ${interval} ${baseFreq}s`;
}