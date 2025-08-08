/**
 * Validation utilities for data integrity and type safety
 */

// UUID v4 validation regex
const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export class ValidationUtils {
  /**
   * Validate UUID v4 string
   */
  static isValidUUID(uuid: string): boolean {
    return typeof uuid === 'string' && UUID_V4_REGEX.test(uuid);
  }

  /**
   * Validate email format
   */
  static isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Validate that amount in cents is a valid integer
   */
  static isValidCentAmount(cents: unknown): cents is number {
    return typeof cents === 'number' && Number.isInteger(cents) && isFinite(cents);
  }

  /**
   * Validate currency code (3-letter ISO code)
   */
  static isValidCurrencyCode(code: string): boolean {
    return typeof code === 'string' && /^[A-Z]{3}$/.test(code);
  }

  /**
   * Validate date string (ISO format)
   */
  static isValidISODate(dateString: string): boolean {
    const date = new Date(dateString);
    return !isNaN(date.getTime()) && dateString.includes('T');
  }

  /**
   * Validate date string (YYYY-MM-DD format)
   */
  static isValidDateString(dateString: string): boolean {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(dateString)) return false;
    
    const date = new Date(dateString);
    return !isNaN(date.getTime());
  }

  /**
   * Validate percentage (0-100)
   */
  static isValidPercentage(percentage: number): boolean {
    return typeof percentage === 'number' && 
           percentage >= 0 && 
           percentage <= 100 && 
           isFinite(percentage);
  }

  /**
   * Validate confidence score (0-1)
   */
  static isValidConfidence(confidence: number): boolean {
    return typeof confidence === 'number' && 
           confidence >= 0 && 
           confidence <= 1 && 
           isFinite(confidence);
  }

  /**
   * Validate string is not empty or just whitespace
   */
  static isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0;
  }

  /**
   * Validate positive number
   */
  static isPositiveNumber(value: unknown): value is number {
    return typeof value === 'number' && value > 0 && isFinite(value);
  }

  /**
   * Validate non-negative number
   */
  static isNonNegativeNumber(value: unknown): value is number {
    return typeof value === 'number' && value >= 0 && isFinite(value);
  }

  /**
   * Validate array is not empty
   */
  static isNonEmptyArray<T>(value: unknown): value is T[] {
    return Array.isArray(value) && value.length > 0;
  }

  /**
   * Validate transaction description
   */
  static isValidTransactionDescription(description: string): boolean {
    return this.isNonEmptyString(description) && 
           description.length <= 255 && 
           description.length >= 1;
  }

  /**
   * Validate merchant name
   */
  static isValidMerchantName(merchant: string): boolean {
    return this.isNonEmptyString(merchant) && 
           merchant.length <= 100;
  }

  /**
   * Validate budget/goal name
   */
  static isValidName(name: string, maxLength: number = 100): boolean {
    return this.isNonEmptyString(name) && 
           name.length <= maxLength;
  }

  /**
   * Sanitize string input (remove potentially harmful characters)
   */
  static sanitizeString(input: string): string {
    return input
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
      .replace(/[<>]/g, '') // Remove angle brackets
      .trim();
  }

  /**
   * Validate and sanitize user input
   */
  static validateAndSanitizeInput(
    input: string, 
    maxLength: number = 255,
    required: boolean = true
  ): { isValid: boolean; sanitized: string; error?: string } {
    if (required && !this.isNonEmptyString(input)) {
      return { isValid: false, sanitized: '', error: 'Input is required' };
    }

    if (!required && (!input || input.trim() === '')) {
      return { isValid: true, sanitized: '' };
    }

    const sanitized = this.sanitizeString(input);
    
    if (sanitized.length > maxLength) {
      return { 
        isValid: false, 
        sanitized, 
        error: `Input must be ${maxLength} characters or less` 
      };
    }

    return { isValid: true, sanitized };
  }

  /**
   * Validate ML confidence threshold
   */
  static isValidConfidenceThreshold(threshold: number): boolean {
    return this.isValidConfidence(threshold) && threshold >= 0.1; // Minimum 10%
  }

  /**
   * Validate pagination parameters
   */
  static validatePaginationParams(page?: number, limit?: number): {
    page: number;
    limit: number;
    isValid: boolean;
    error?: string;
  } {
    const defaultPage = 1;
    const defaultLimit = 20;
    const maxLimit = 100;

    const validatedPage = page && page > 0 ? Math.floor(page) : defaultPage;
    const validatedLimit = limit && limit > 0 ? Math.min(Math.floor(limit), maxLimit) : defaultLimit;

    return {
      page: validatedPage,
      limit: validatedLimit,
      isValid: true
    };
  }

  /**
   * Validate date range
   */
  static validateDateRange(startDate?: string, endDate?: string): {
    isValid: boolean;
    error?: string;
  } {
    if (!startDate && !endDate) {
      return { isValid: true };
    }

    if (startDate && !this.isValidDateString(startDate)) {
      return { isValid: false, error: 'Invalid start date format' };
    }

    if (endDate && !this.isValidDateString(endDate)) {
      return { isValid: false, error: 'Invalid end date format' };
    }

    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      
      if (start > end) {
        return { isValid: false, error: 'Start date must be before end date' };
      }

      // Check if date range is reasonable (not more than 5 years)
      const diffInDays = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
      if (diffInDays > 365 * 5) {
        return { isValid: false, error: 'Date range cannot exceed 5 years' };
      }
    }

    return { isValid: true };
  }
}