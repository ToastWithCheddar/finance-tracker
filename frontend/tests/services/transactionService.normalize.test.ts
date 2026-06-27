/**
 * Sanity test for the snake<->camel normalization layer in
 * frontend/src/services/transactionService.ts. The service's
 * `normalizeTransaction` is private, so we exercise it indirectly via
 * `getTransactions()` against an MSW handler that returns the real backend
 * (snake_case) shape, and verify the consumer-visible camelCase fields.
 *
 * Round-trip note: the helper `snakeToCamelShallow` in api.ts is a separate
 * utility — we check it here too so a future deletion is caught.
 */
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';

const API = 'http://localhost:8000/api';

describe('transactionService normalization', () => {
  it('maps snake_case backend fields to camelCase frontend fields', async () => {
    server.use(
      http.get(`${API}/transactions`, () =>
        HttpResponse.json({
          items: [
            {
              id: 'tx-42',
              user_id: 'u-1',
              account_id: 'a-1',
              account_name: 'Checking',
              category_id: 'c-1',
              category_name: 'Food',
              amount_cents: 9900,
              currency: 'USD',
              description: 'Groceries',
              transaction_date: '2026-04-15',
              is_transfer: false,
              tags: ['weekly'],
              created_at: '2026-04-15T08:00:00Z',
              updated_at: '2026-04-15T08:00:00Z',
              status: 'posted',
            },
          ],
          total: 1,
          page: 1,
          per_page: 25,
          pages: 1,
        }),
      ),
    );

    const { transactionService } = await import('@/services/transactionService');
    const res = await transactionService.getTransactions();

    expect(res.items).toHaveLength(1);
    const tx = res.items[0] as Record<string, unknown>;
    expect(tx.userId).toBe('u-1');
    expect(tx.accountId).toBe('a-1');
    expect(tx.accountName).toBe('Checking');
    expect(tx.categoryId).toBe('c-1');
    expect(tx.amountCents).toBe(9900);
    expect(tx.transactionDate).toBe('2026-04-15');
    expect(tx.isTransfer).toBe(false);
  });

  it('snakeToCamelShallow flips a single-level snake_case object', async () => {
    const { snakeToCamelShallow } = await import('@/services/api');
    const out = snakeToCamelShallow({
      access_token: 'a',
      refresh_token: 'b',
      expires_in: 1800,
    }) as Record<string, unknown>;
    expect(out).toMatchObject({
      accessToken: 'a',
      refreshToken: 'b',
      expiresIn: 1800,
    });
  });
});
