/**
 * authStore behavior:
 *  - login persists user + isAuthenticated
 *  - logout clears state + tokens
 *  - refreshToken keeps the existing user when backend omits it
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import {
  clearTokens,
  readStoredAccessToken,
  readStoredRefreshToken,
  seedTokens,
} from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

beforeEach(() => {
  clearTokens();
  window.localStorage.clear();
});

afterEach(() => {
  clearTokens();
  window.localStorage.clear();
});

describe('authStore', () => {
  it('login persists user + tokens on success', async () => {
    const { useAuthStore } = await import('@/stores/authStore');

    await useAuthStore.getState().login({
      email: 'test@example.com',
      password: 'pw12345!',
    } as Parameters<ReturnType<typeof useAuthStore.getState>['login']>[0]);

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe('test@example.com');
    expect(readStoredAccessToken()).toBe('access-token-initial');
    expect(readStoredRefreshToken()).toBe('refresh-token-initial');
  });

  it('logout clears user, isAuthenticated, and tokens', async () => {
    const { useAuthStore } = await import('@/stores/authStore');

    seedTokens();
    useAuthStore.setState({
      user: { id: 'u-1', email: 'test@example.com' } as Parameters<typeof useAuthStore.setState>[0]['user'],
      isAuthenticated: true,
    });

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(readStoredAccessToken()).toBeNull();
    expect(readStoredRefreshToken()).toBeNull();
  });

  it('refreshToken keeps the existing user when backend omits it', async () => {
    const { useAuthStore } = await import('@/stores/authStore');

    // Pre-seed an authenticated state with a refresh token in storage.
    seedTokens({
      accessToken: 'expired',
      refreshToken: 'valid-refresh',
      expiresInSeconds: 1800,
    });
    const existingUser = {
      id: 'u-1',
      email: 'existing@example.com',
      full_name: 'Existing',
    } as Parameters<typeof useAuthStore.setState>[0]['user'];
    useAuthStore.setState({ user: existingUser, isAuthenticated: true });

    // authStore.refreshToken POSTs to /auth/refresh expecting an AuthResponse
    // envelope (user + tokens). Override the default refresh handler.
    server.use(
      http.post(`${API}/auth/refresh`, () =>
        HttpResponse.json({
          // user intentionally omitted — store should keep existingUser
          tokens: {
            access_token: 'new-access',
            refresh_token: 'new-refresh',
            token_type: 'bearer',
            expires_in: 1800,
          },
        }),
      ),
    );

    await useAuthStore.getState().refreshToken();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe('existing@example.com');
    expect(readStoredAccessToken()).toBe('new-access');
  });
});
