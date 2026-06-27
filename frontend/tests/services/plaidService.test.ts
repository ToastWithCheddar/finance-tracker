/**
 * plaidService — link-token unwrap (handles both wrapped and direct shapes),
 * exchange-token uses `public_token` as a query param, and connection-status
 * normalization (snake_case fallbacks).
 */
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

describe('plaidService', () => {
  it('createLinkToken returns the unwrapped link_token (direct shape)', async () => {
    seedTokens();
    const { plaidService } = await import('@/services/plaidService');
    const tok = await plaidService.createLinkToken();
    expect(tok.link_token).toBe('link-sandbox-token');
    expect(tok.environment).toBe('sandbox');
    clearTokens();
  });

  it('createLinkToken handles the wrapped {success, data:{...}} shape', async () => {
    seedTokens();
    server.use(
      http.post(`${API}/accounts/plaid/link-token`, () =>
        HttpResponse.json({
          success: true,
          data: {
            success: true,
            link_token: 'wrapped-token',
            expiration: '2026-04-15T11:00:00Z',
            request_id: 'req-2',
            environment: 'sandbox',
          },
        }),
      ),
    );
    const { plaidService } = await import('@/services/plaidService');
    const tok = await plaidService.createLinkToken();
    expect(tok.link_token).toBe('wrapped-token');
    clearTokens();
  });

  it('exchangeToken sends public_token in the query string', async () => {
    seedTokens();
    let capturedUrl: URL | null = null;
    server.use(
      http.post(`${API}/accounts/plaid/exchange-token`, ({ request }) => {
        capturedUrl = new URL(request.url);
        return HttpResponse.json({
          success: true,
          message: 'Connected',
          data: {
            accounts: [],
            accounts_created: 0,
            institution: 'X',
          },
        });
      }),
    );

    const { plaidService } = await import('@/services/plaidService');
    await plaidService.exchangeToken({
      public_token: 'public-sandbox-abc',
      metadata: {
        institution: { name: 'Test', institution_id: 'ins_1' },
        accounts: [],
      },
    });
    expect(capturedUrl).not.toBeNull();
    expect(capturedUrl!.searchParams.get('public_token')).toBe('public-sandbox-abc');
    clearTokens();
  });

  it('getConnectionStatus normalizes raw account fields to PlaidAccount shape', async () => {
    seedTokens();
    server.use(
      http.get(`${API}/accounts/connection-status`, () =>
        HttpResponse.json({
          total_connections: 1,
          accounts: [
            {
              id: 'a-1',
              name: 'Checking',
              type: 'depository',
              balance: 100, // dollars — should be coerced to cents
              currency: 'USD',
              plaid_account_id: 'plaid-1',
              health_status: 'healthy',
            },
          ],
        }),
      ),
    );

    const { plaidService } = await import('@/services/plaidService');
    const status = await plaidService.getConnectionStatus({ useCache: false });
    expect(status.connected).toBe(true);
    expect(status.accounts).toHaveLength(1);
    expect(status.accounts[0].account_type).toBe('depository');
    expect(status.accounts[0].balance_cents).toBe(10000);
    expect(status.accounts[0].connection_health).toBe('healthy');
    clearTokens();
  });
});
