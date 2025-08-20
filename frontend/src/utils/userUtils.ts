import type { UserProfile } from '../services/userService';

/**
 * Formats a date string into a human-readable format
 */
export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

/**
 * Generates user initials from various name fields
 */
export const getInitials = (
  firstName?: string, 
  lastName?: string, 
  displayName?: string,
  fallbackEmail?: string
): string => {
  if (displayName) {
    return displayName.charAt(0).toUpperCase();
  }
  if (firstName && lastName) {
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
  }
  if (firstName) {
    return firstName.charAt(0).toUpperCase();
  }
  if (fallbackEmail) {
    return fallbackEmail.charAt(0).toUpperCase();
  }
  return 'U';
};

/**
 * Gets the display name for a user from their profile
 */
export const getDisplayName = (profile: UserProfile): string => {
  if (profile.display_name) return profile.display_name;
  if (profile.first_name && profile.last_name) {
    return `${profile.first_name} ${profile.last_name}`;
  }
  if (profile.first_name) return profile.first_name;
  return 'User';
};

/**
 * Gets initials for a user profile
 */
export const getUserInitials = (profile: UserProfile): string => {
  return getInitials(
    profile.first_name,
    profile.last_name,
    profile.display_name,
    profile.email
  );
};