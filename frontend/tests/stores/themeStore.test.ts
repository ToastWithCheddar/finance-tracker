/**
 * themeStore — persistence + auto-mode resolution.
 *
 * - setTheme writes the preference to localStorage and resolves actualTheme.
 * - initializeTheme reads the persisted preference and resolves against the
 *   system theme reported by matchMedia.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => {
  document.documentElement.className = '';
  document.documentElement.removeAttribute('data-theme');
  window.localStorage.clear();
});

describe('themeStore', () => {
  it('setTheme persists preference and updates actualTheme', async () => {
    const { useThemeStore } = await import('@/stores/themeStore');
    useThemeStore.getState().setTheme('dark');
    expect(useThemeStore.getState().theme).toBe('dark');
    expect(useThemeStore.getState().actualTheme).toBe('dark');
    expect(window.localStorage.getItem('theme-preference')).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('initializeTheme reads persisted "light" preference', async () => {
    window.localStorage.setItem('theme-preference', 'light');
    const { useThemeStore } = await import('@/stores/themeStore');
    useThemeStore.getState().initializeTheme();
    expect(useThemeStore.getState().theme).toBe('light');
    expect(useThemeStore.getState().actualTheme).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('auto mode resolves actualTheme from prefers-color-scheme', async () => {
    // Override matchMedia to report dark
    (window.matchMedia as any) = vi.fn().mockImplementation((q: string) => ({
      matches: q.includes('dark'),
      media: q,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    window.localStorage.setItem('theme-preference', 'auto');
    const { useThemeStore } = await import('@/stores/themeStore');
    useThemeStore.getState().initializeTheme();
    expect(useThemeStore.getState().theme).toBe('auto');
    expect(useThemeStore.getState().systemTheme).toBe('dark');
    expect(useThemeStore.getState().actualTheme).toBe('dark');
  });
});
