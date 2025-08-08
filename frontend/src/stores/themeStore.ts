import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'auto';

interface ThemeState {
  theme: Theme;
  systemTheme: 'light' | 'dark';
  actualTheme: 'light' | 'dark'; // The actual theme being used (resolved from auto)
  
  // Actions
  setTheme: (theme: Theme) => void;
  initializeTheme: () => void;
  applyTheme: () => void;
}

const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'light';
  
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const applyThemeToDOM = (theme: 'light' | 'dark') => {
  if (typeof document === 'undefined') return;
  
  const root = document.documentElement;
  
  if (theme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  
  // Also set a data attribute for CSS-in-JS libraries
  root.setAttribute('data-theme', theme);
  
  // Update meta theme-color for mobile browsers
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute(
      'content', 
      theme === 'dark' ? '#1f2937' : '#ffffff'
    );
  }
};

const resolveActualTheme = (theme: Theme, systemTheme: 'light' | 'dark'): 'light' | 'dark' => {
  return theme === 'auto' ? systemTheme : theme;
};

export const useThemeStore = create<ThemeState>()(
  subscribeWithSelector((set, get) => ({
    theme: 'auto',
    systemTheme: 'light',
    actualTheme: 'light',

    setTheme: (theme: Theme) => {
      const { systemTheme } = get();
      const actualTheme = resolveActualTheme(theme, systemTheme);
      
      set({ theme, actualTheme });
      
      // Apply theme immediately
      applyThemeToDOM(actualTheme);
      
      // Store preference in localStorage
      try {
        localStorage.setItem('theme-preference', theme);
      } catch (error) {
        console.warn('Failed to save theme preference:', error);
      }
    },

    initializeTheme: () => {
      const systemTheme = getSystemTheme();
      
      // Get stored theme preference or default to 'auto'
      let storedTheme: Theme = 'auto';
      try {
        const stored = localStorage.getItem('theme-preference');
        if (stored && ['light', 'dark', 'auto'].includes(stored)) {
          storedTheme = stored as Theme;
        }
      } catch (error) {
        console.warn('Failed to read theme preference:', error);
      }
      
      const actualTheme = resolveActualTheme(storedTheme, systemTheme);
      
      set({ 
        theme: storedTheme, 
        systemTheme, 
        actualTheme 
      });
      
      // Apply theme to DOM
      applyThemeToDOM(actualTheme);
    },

    applyTheme: () => {
      const { actualTheme } = get();
      applyThemeToDOM(actualTheme);
    },
  }))
);

// Subscribe to system theme changes
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  
  const handleSystemThemeChange = (e: MediaQueryListEvent) => {
    const systemTheme = e.matches ? 'dark' : 'light';
    const { theme } = useThemeStore.getState();
    const actualTheme = resolveActualTheme(theme, systemTheme);
    
    useThemeStore.setState({ 
      systemTheme, 
      actualTheme 
    });
    
    // Apply theme if currently using auto
    if (theme === 'auto') {
      applyThemeToDOM(actualTheme);
    }
  };
  
  // Modern browsers
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handleSystemThemeChange);
  } else {
    // Legacy browsers
    mediaQuery.addListener(handleSystemThemeChange);
  }
}

// Initialize theme on store creation
if (typeof window !== 'undefined') {
  // Use setTimeout to ensure DOM is ready
  setTimeout(() => {
    useThemeStore.getState().initializeTheme();
  }, 0);
}

// Convenience hooks for components
export const useTheme = () => useThemeStore(state => state.actualTheme);
export const useThemePreference = () => useThemeStore(state => state.theme);
export const useThemeActions = () => useThemeStore(state => ({
  setTheme: state.setTheme,
  initializeTheme: state.initializeTheme,
  applyTheme: state.applyTheme,
}));

// Utility function to sync theme with user preferences
export const syncThemeWithPreferences = (userTheme: string) => {
  const validTheme = ['light', 'dark', 'auto'].includes(userTheme) ? userTheme as Theme : 'auto';
  useThemeStore.getState().setTheme(validTheme);
};