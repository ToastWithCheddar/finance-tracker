import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  userPreferencesService, 
  type UserPreferences,
  type UserPreferencesUpdate 
} from '../services/userPreferencesService';
import { syncThemeWithPreferences } from '../stores/themeStore';
import toast from 'react-hot-toast';

// Query keys
const USER_PREFERENCES_KEYS = {
  all: ['user-preferences'] as const,
  preferences: () => [...USER_PREFERENCES_KEYS.all, 'current'] as const,
} as const;

// Get user preferences
export function useUserPreferences() {
  return useQuery({
    queryKey: USER_PREFERENCES_KEYS.preferences(),
    queryFn: () => userPreferencesService.getPreferences(),
    staleTime: 10 * 60 * 1000, // 10 minutes (preferences don't change often)
    gcTime: 30 * 60 * 1000, // 30 minutes
    retry: 1, // Only retry once for preferences
  });
}

// Update user preferences mutation
export function useUpdateUserPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (preferences: UserPreferencesUpdate) => {
      // Validate preferences before sending
      const errors = userPreferencesService.validatePreferences(preferences);
      if (errors.length > 0) {
        throw new Error(errors.join(', '));
      }
      
      return userPreferencesService.updatePreferences(preferences);
    },
    onSuccess: (updatedPreferences) => {
      // Update cache
      queryClient.setQueryData(
        USER_PREFERENCES_KEYS.preferences(),
        updatedPreferences
      );
      
      // Sync theme with preferences if theme was updated
      if (updatedPreferences.theme) {
        syncThemeWithPreferences(updatedPreferences.theme);
      }
      
      // Update local storage as backup
      userPreferencesService.setLocalPreferences(updatedPreferences);
      
      // Show success message
      toast.success('Preferences saved successfully!');
    },
    onError: (error) => {
      console.error('Failed to save preferences:', error);
      toast.error(`Failed to save preferences: ${error.message}`);
    },
  });
}

// Reset preferences to defaults mutation
export function useResetUserPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => userPreferencesService.resetToDefaults(),
    onSuccess: (defaultPreferences) => {
      // Update cache
      queryClient.setQueryData(
        USER_PREFERENCES_KEYS.preferences(),
        defaultPreferences
      );
      
      // Sync theme
      syncThemeWithPreferences(defaultPreferences.theme);
      
      // Update local storage
      userPreferencesService.setLocalPreferences(defaultPreferences);
      
      toast.success('Preferences reset to defaults!');
    },
    onError: (error) => {
      console.error('Failed to reset preferences:', error);
      toast.error(`Failed to reset preferences: ${error.message}`);
    },
  });
}

// Hook to check if preferences are loaded and valid
export function usePreferencesStatus() {
  const { data, isLoading, error, isError } = useUserPreferences();
  
  return {
    isLoaded: !isLoading && !!data,
    isLoading,
    hasError: isError,
    error,
    preferences: data,
  };
}

// Hook for specific preference values with fallbacks
export function usePreference<K extends keyof UserPreferences>(
  key: K
): UserPreferences[K] {
  const { data } = useUserPreferences();
  return data?.[key] ?? userPreferencesService.getLocalPreferences()[key];
}

// Hook for multiple preference values
export function usePreferences<K extends keyof UserPreferences>(
  keys: K[]
): Pick<UserPreferences, K> {
  const { data } = useUserPreferences();
  const localPrefs = userPreferencesService.getLocalPreferences();
  
  const result = {} as Pick<UserPreferences, K>;
  keys.forEach(key => {
    result[key] = data?.[key] ?? localPrefs[key];
  });
  
  return result;
}

// Utility hook that combines update operations
export function usePreferencesActions() {
  const updateMutation = useUpdateUserPreferences();
  const resetMutation = useResetUserPreferences();

  return {
    update: updateMutation.mutate,
    updateAsync: updateMutation.mutateAsync,
    reset: resetMutation.mutate,
    resetAsync: resetMutation.mutateAsync,
    
    isUpdating: updateMutation.isPending,
    isResetting: resetMutation.isPending,
    isBusy: updateMutation.isPending || resetMutation.isPending,
    
    updateError: updateMutation.error,
    resetError: resetMutation.error,
  };
}

// Hook for preference options (useful for dropdowns)
export function usePreferenceOptions() {
  return {
    currencies: userPreferencesService.getCurrencyOptions(),
    dateFormats: userPreferencesService.getDateFormatOptions(),
    themes: userPreferencesService.getThemeOptions(),
    accountTypes: userPreferencesService.getAccountTypeOptions(),
    backupFrequencies: userPreferencesService.getBackupFrequencyOptions(),
    startupPages: userPreferencesService.getStartupPageOptions(),
  };
}

// Hook to format values according to user preferences
export function useFormattingHelpers() {
  const preferences = useUserPreferences().data;
  
  return {
    formatCurrency: (amount: number) => 
      userPreferencesService.formatCurrency(amount, preferences?.currency),
    formatDate: (date: Date | string) => 
      userPreferencesService.formatDate(date, preferences?.date_format),
    itemsPerPage: preferences?.items_per_page ?? 25,
  };
}