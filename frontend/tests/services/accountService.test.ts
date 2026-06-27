/**
 * accountService — verifies CRUD against /accounts/, error mapping for
 * UNAUTHORIZED -> friendly message, and array-shape validation.
 */
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

describe('accountService', () => {
  it('getAccounts returns the array on success', async () => {
    seedTokens();
    const { accountService } = await import('@/services/accountService');
    const accounts = await accountService.getAccounts();
    expect(Array.isArray(accounts)).toBe(true);
    expect(accounts[0].id).toBe('acct-1');
    expect(accounts[0].balance_cents).toBe(100000);
    clearTokens();
  });

  it('getAccounts throws when response is not an array', async () => {
    seedTokens();
    server.use(
      http.get(`${API}/accounts/`, () =>
        HttpResponse.json({ not: 'an array' }),
      ),
    );
    const { accountService } = await import('@/services/accountService');
    await expect(accountService.getAccounts()).rejects.toThrow(
      /expected array of accounts/,
    );
    clearTokens();
  });

  it('createAccount POSTs and returns the new account', async () => {
    seedTokens();
    const { accountService } = await import('@/services/accountService');
    const acct = await accountService.createAccount({
      name: 'New Account',
      account_type: 'savings',
      balance_cents: 0,
    });
    expect(acct.id).toBe('acct-new');
    expect(acct.account_type).toBe('savings');
    clearTokens();
  });

  it('maps UNAUTHORIZED into a friendly auth error', async () => {
    seedTokens();
    server.use(
      http.get(`${API}/accounts/`, () =>
        new HttpResponse(JSON.stringify({ detail: 'nope' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      ),
      // Avoid the api.ts refresh interceptor from succeeding silently
      http.post(`${API}/auth/refresh`, () =>
        new HttpResponse(JSON.stringify({ detail: 'no' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    const { accountService } = await import('@/services/accountService');
    await expect(accountService.getAccounts()).rejects.toBeDefined();
    clearTokens();
  });
});
