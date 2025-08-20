import { useMemo } from 'react';
import { NIVO_CHART_THEME, NIVO_CHART_THEME_DARK } from '../utils/chartColors';

/**
 * Custom hook for consistent chart theming across the application
 * Automatically detects dark/light mode and returns appropriate Nivo theme
 */
export function useChartTheme() {
  // Detect if user prefers dark mode
  const isDarkMode = useMemo(() => {
    if (typeof window === 'undefined') return false;
    
    // Check for explicit dark mode class on document
    if (document.documentElement.classList.contains('dark')) {
      return true;
    }
    
    // Fallback to system preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }, []);

  // Return appropriate theme based on mode
  const theme = useMemo(() => {
    return isDarkMode ? NIVO_CHART_THEME_DARK : NIVO_CHART_THEME;
  }, [isDarkMode]);

  return {
    theme,
    isDarkMode,
  };
}