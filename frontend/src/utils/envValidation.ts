/**
 * Environment variable validation utility
 * Ensures required environment variables are present and valid
 */

interface EnvConfig {
  VITE_API_URL?: string;
  VITE_APP_NAME?: string;
  VITE_APP_VERSION?: string;
  VITE_ENABLE_DEVTOOLS?: string;
  VITE_ADMIN_BYPASS?: string;
}

class EnvironmentValidator {
  private readonly requiredVars: (keyof EnvConfig)[] = [
    'VITE_API_URL',
  ];

  private readonly optionalVars: (keyof EnvConfig)[] = [
    'VITE_APP_NAME',
    'VITE_APP_VERSION',
    'VITE_ENABLE_DEVTOOLS',
    'VITE_ADMIN_BYPASS',
  ];

  /**
   * Validate all environment variables
   */
  validateEnvironment(): { isValid: boolean; errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check required variables
    for (const varName of this.requiredVars) {
      const value = import.meta.env[varName];
      if (!value) {
        errors.push(`Missing required environment variable: ${varName}`);
      } else {
        // Validate specific variables
        if (varName === 'VITE_API_URL' && !this.isValidUrl(value)) {
          errors.push(`Invalid VITE_API_URL format: ${value}`);
        }
      }
    }

    // Check for security issues
    if (import.meta.env.PROD) {
      // In production, certain variables should not be enabled
      if (import.meta.env.VITE_ADMIN_BYPASS === 'true') {
        warnings.push('VITE_ADMIN_BYPASS is enabled in production - this is a security risk');
      }
      
      if (import.meta.env.VITE_ENABLE_DEVTOOLS === 'true') {
        warnings.push('VITE_ENABLE_DEVTOOLS is enabled in production - consider disabling');
      }
    }

    // Check for missing optional variables
    for (const varName of this.optionalVars) {
      const value = import.meta.env[varName];
      if (!value) {
        warnings.push(`Optional environment variable not set: ${varName}`);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Get environment configuration with defaults
   */
  getConfig(): Required<EnvConfig> {
    return {
      VITE_API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
      VITE_APP_NAME: import.meta.env.VITE_APP_NAME || 'Finance Tracker',
      VITE_APP_VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
      VITE_ENABLE_DEVTOOLS: import.meta.env.VITE_ENABLE_DEVTOOLS || 'false',
      VITE_ADMIN_BYPASS: import.meta.env.VITE_ADMIN_BYPASS || 'false',
    };
  }

  /**
   * Validate URL format
   */
  private isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Log validation results
   */
  logValidationResults(): void {
    const { isValid, errors, warnings } = this.validateEnvironment();
    
    if (!isValid) {
      console.error('❌ Environment validation failed:');
      errors.forEach(error => console.error(`  • ${error}`));
    } else {
      console.log('✅ Environment validation passed');
    }

    if (warnings.length > 0) {
      console.warn('⚠️ Environment warnings:');
      warnings.forEach(warning => console.warn(`  • ${warning}`));
    }

    if (import.meta.env.DEV) {
      console.log('🔧 Environment configuration:', this.getConfig());
    }
  }
}

// Create and export singleton
export const envValidator = new EnvironmentValidator();

// Validate on import (only in development or if explicitly enabled)
if (import.meta.env.DEV || import.meta.env.VITE_VALIDATE_ENV === 'true') {
  envValidator.logValidationResults();
}