/**
 * Currency handling utilities for consistent money formatting and conversion
 * All money values are stored as integer cents in the system
 */

export interface CurrencyOptions {
  currency?: string;
  locale?: string;
  showCents?: boolean;
  showSign?: boolean;
  compact?: boolean;
}

export class CurrencyUtils {
  private static defaultCurrency = 'USD';
  private static defaultLocale = 'en-US';

  /**
   * Convert dollars to cents (for storage)
   */
  static dollarsToCents(dollars: number): number {
    return Math.round(dollars * 100);
  }

  /**
   * Convert cents to dollars (for display)
   */
  static centsToDollars(cents: number): number {
    return cents / 100;
  }

  /**
   * Format cents as currency for display
   */
  static formatCents(
    amountCents: number, 
    options: CurrencyOptions = {}
  ): string {
    const {
      currency = this.defaultCurrency,
      locale = this.defaultLocale,
      showCents = true,
      showSign = false,
      compact = false
    } = options;

    const dollars = this.centsToDollars(Math.abs(amountCents));
    
    const formatter = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: showCents ? 2 : 0,
      maximumFractionDigits: showCents ? 2 : 0,
      notation: compact ? 'compact' : 'standard'
    });

    const formatted = formatter.format(dollars);
    
    if (showSign && amountCents !== 0) {
      return amountCents > 0 ? `+${formatted}` : `-${formatted}`;
    }
    
    return amountCents < 0 ? `-${formatted}` : formatted;
  }

  /**
   * Format dollars as currency (for legacy support)
   */
  static formatDollars(
    dollars: number, 
    options: CurrencyOptions = {}
  ): string {
    return this.formatCents(this.dollarsToCents(dollars), options);
  }

  /**
   * Parse currency string to cents
   */
  static parseToCents(currencyString: string): number {
    // Remove currency symbols, spaces, and commas
    const cleanString = currencyString
      .replace(/[^\d.-]/g, '')
      .trim();
    
    const dollars = parseFloat(cleanString) || 0;
    return this.dollarsToCents(dollars);
  }

  /**
   * Format amount with appropriate sign for transaction type
   */
  static formatTransactionAmount(
    amountCents: number,
    isIncome: boolean,
    options: CurrencyOptions = {}
  ): string {
    const absAmount = Math.abs(amountCents);
    const displayAmount = isIncome ? absAmount : -absAmount;
    
    return this.formatCents(displayAmount, {
      ...options,
      showSign: true
    });
  }

  /**
   * Format amount for different contexts
   */
  static formatForContext(
    amountCents: number,
    context: 'transaction' | 'balance' | 'budget' | 'goal' | 'compact',
    options: CurrencyOptions = {}
  ): string {
    switch (context) {
      case 'transaction':
        return this.formatCents(amountCents, { ...options, showSign: true });
      
      case 'balance':
        return this.formatCents(amountCents, { ...options, showCents: true });
      
      case 'budget':
        return this.formatCents(Math.abs(amountCents), { ...options, showCents: true });
      
      case 'goal':
        return this.formatCents(Math.abs(amountCents), { ...options, showCents: false });
      
      case 'compact':
        return this.formatCents(amountCents, { ...options, compact: true, showCents: false });
      
      default:
        return this.formatCents(amountCents, options);
    }
  }

  /**
   * Get currency symbol for a given currency code
   */
  static getCurrencySymbol(currency: string = this.defaultCurrency, locale: string = this.defaultLocale): string {
    const formatter = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
    
    // Format 0 and extract just the symbol
    const formatted = formatter.format(0);
    return formatted.replace(/[\d\s]/g, '');
  }

  /**
   * Validate that an amount in cents is valid (no fractional cents)
   */
  static isValidCentAmount(cents: number): boolean {
    return Number.isInteger(cents) && isFinite(cents);
  }

  /**
   * Round to nearest cent (useful for calculations)
   */
  static roundToCents(dollars: number): number {
    return this.dollarsToCents(dollars);
  }

  /**
   * Calculate percentage of budget used
   */
  static calculateBudgetPercentage(spentCents: number, budgetCents: number): number {
    if (budgetCents === 0) return 0;
    return Math.round((spentCents / budgetCents) * 100);
  }

  /**
   * Calculate goal progress percentage
   */
  static calculateGoalProgress(currentCents: number, targetCents: number): number {
    if (targetCents === 0) return 0;
    return Math.min(Math.round((currentCents / targetCents) * 100), 100);
  }

  /**
   * Format percentage with appropriate precision
   */
  static formatPercentage(percentage: number, precision: number = 1): string {
    return `${percentage.toFixed(precision)}%`;
  }

  /**
   * Get appropriate color class for amount (for UI styling)
   */
  static getAmountColorClass(amountCents: number, context: 'transaction' | 'balance' | 'budget'): string {
    if (context === 'transaction') {
      return amountCents > 0 ? 'text-green-600' : 'text-red-600';
    }
    
    if (context === 'balance') {
      return amountCents >= 0 ? 'text-green-600' : 'text-red-600';
    }
    
    if (context === 'budget') {
      // For budget context, red means over budget (negative remaining)
      return amountCents < 0 ? 'text-red-600' : 'text-green-600';
    }
    
    return 'text-gray-900';
  }

  /**
   * Compare two amounts with tolerance for floating point precision
   */
  static areAmountsEqual(cents1: number, cents2: number, tolerance: number = 0): boolean {
    return Math.abs(cents1 - cents2) <= tolerance;
  }

  /**
   * Set default currency and locale
   */
  static setDefaults(currency: string, locale: string): void {
    this.defaultCurrency = currency;
    this.defaultLocale = locale;
  }

  /**
   * Get supported currencies (could be expanded to fetch from API)
   */
  static getSupportedCurrencies(): Array<{ code: string; name: string; symbol: string }> {
    return [
      { code: 'USD', name: 'US Dollar', symbol: '$' },
      { code: 'EUR', name: 'Euro', symbol: '€' },
      { code: 'GBP', name: 'British Pound', symbol: '£' },
      { code: 'CAD', name: 'Canadian Dollar', symbol: 'C$' },
      { code: 'AUD', name: 'Australian Dollar', symbol: 'A$' },
      { code: 'JPY', name: 'Japanese Yen', symbol: '¥' },
    ];
  }
}

// Export a simple formatCurrency function for backwards compatibility
export function formatCurrency(amountCents: number): string {
  return CurrencyUtils.formatCents(amountCents);
}