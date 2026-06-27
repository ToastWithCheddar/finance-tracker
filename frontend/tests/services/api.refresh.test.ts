/**
 * EXPECTED FAILURE — documents FE-SEC-003.
 *
 * The backend `/auth/refresh` returns snake_case (see
 * backend/app/schemas/auth.py:30 — TokenResponse with access_token /
 * refresh_token). The frontend's apiClient.request() refresh interceptor at
 * frontend/src/services/api.ts:309-314 reads `refreshData.accessToken` and
 * `refreshData.refreshToken` (camelCase). Because those keys are absent in
 * the real response, the interceptor clears tokens and surfaces the original
 * 401 instead of retrying with a fresh access token.
 *
 * This test simulates the real backend shape via MSW and asserts that the
 * retry succeeds. It is marked `it.fails(...)` so it stays green in the suite
 * while documenting the open bug — once `api.ts` is fixed to read the
 * snake_case fields, flip `it.fails` -> `it`.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import { seedTokens, clearTokens, readStoredAccessToken } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

beforeEach(() => {
  clearTokens();
  seedTokens({
    accessToken: 'expired-access-token',
    refreshToken: 'valid-refresh-token',
    expiresInSeconds: 1800,
  });
});

afterEach(() => {
  clearTokens();
});

describe('apiClient refresh interceptor (FE-SEC-003)', () => {
  it(
    'retries the original request after a snake_case refresh response',
    async () => {
      // Import lazily so vitest module isolation gives us a fresh apiClient
      // singleton with the seeded tokens visible.
      const { apiClient } = await import('@/services/api');

      let protectedHits = 0;
      server.use(
        http.get(`${API}/transactions`, ({ request }) => {
          protectedHits += 1;
          const auth = request.headers.get('authorization') ?? '';
          if (auth.includes('expired-access-token')) {
            return new HttpResponse(
              JSON.stringify({ detail: 'token expired' }),
              { status: 401, headers: { 'content-type': 'application/json' } },
            );
          }
          return HttpResponse.json({
            items: [],
            total: 0,
            page: 1,
            per_page: 25,
            pages: 0,
          });
        }),
        http.post(`${API}/auth/refresh`, () => {
          // Real backend shape (snake_case).
          return HttpResponse.json({
            access_token: 'fresh-access-token',
            refresh_token: 'fresh-refresh-token',
            token_type: 'bearer',
            expires_in: 1800,
          });
        }),
      );

      const result = await apiClient.get<{ items: unknown[]; total: number }>(
        '/transactions',
      );

      // If the bug is fixed, the retry succeeds, the protected endpoint is
      // hit twice (once with the expired token, once with the fresh one),
      // and the new access token is persisted.
      expect(result.total).toBe(0);
      expect(protectedHits).toBe(2);
      expect(readStoredAccessToken()).toBe('fresh-access-token');
    },
  );

  it('clears tokens when refresh response is unparseable (sanity)', async () => {
    const { apiClient } = await import('@/services/api');

    server.use(
      http.get(`${API}/transactions`, () =>
        new HttpResponse(JSON.stringify({ detail: 'nope' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      ),
      http.post(`${API}/auth/refresh`, () =>
        new HttpResponse('not-json', { status: 200 }),
      ),
    );

    await expect(apiClient.get('/transactions')).rejects.toBeDefined();
    // Tokens cleared by the catch path in api.ts:303-305.
    expect(readStoredAccessToken()).toBeNull();
  });
});
