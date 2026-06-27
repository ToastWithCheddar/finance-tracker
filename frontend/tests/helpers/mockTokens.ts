/**
 * Token helpers used across service/store tests. Keep these in sync with the
 * key names declared in frontend/src/services/secureStorage.ts.
 */
export const TOKEN_KEYS = {
  ACCESS: 'finance_access_token',
  REFRESH: 'finance_refresh_token',
  EXPIRES_AT: 'finance_token_expires',
} as const;

export interface MockTokenSet {
  accessToken: string;
  refreshToken: string;
  expiresInSeconds?: number;
}

export function seedTokens(tokens: MockTokenSet = makeTokens()): MockTokenSet {
  const expiresAt =
    Date.now() + (tokens.expiresInSeconds ?? 1800) * 1000;
  sessionStorage.setItem(TOKEN_KEYS.ACCESS, tokens.accessToken);
  sessionStorage.setItem(TOKEN_KEYS.REFRESH, tokens.refreshToken);
  sessionStorage.setItem(TOKEN_KEYS.EXPIRES_AT, String(expiresAt));
  return tokens;
}

export function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_KEYS.ACCESS);
  sessionStorage.removeItem(TOKEN_KEYS.REFRESH);
  sessionStorage.removeItem(TOKEN_KEYS.EXPIRES_AT);
}

export function makeTokens(overrides: Partial<MockTokenSet> = {}): MockTokenSet {
  return {
    accessToken: 'access-token-test',
    refreshToken: 'refresh-token-test',
    expiresInSeconds: 1800,
    ...overrides,
  };
}

export function readStoredAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEYS.ACCESS);
}

export function readStoredRefreshToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEYS.REFRESH);
}
