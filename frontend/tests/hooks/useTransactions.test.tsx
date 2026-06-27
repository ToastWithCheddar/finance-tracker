/**
 * useTransactions / useCreateTransaction — pagination + invalidation behavior.
 * Drives the hooks via renderHook with a fresh QueryClient per test.
 */
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { server } from '../msw/server';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe('useTransactions', () => {
  it('fetches and exposes the paginated list', async () => {
    seedTokens();
    const { wrapper } = makeWrapper();
    const { useTransactions } = await import('@/hooks/useTransactions');
    const { result } = renderHook(() => useTransactions({ page: 1, per_page: 10 }), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items.length).toBeGreaterThan(0);
    expect(result.current.data?.total).toBe(1);
    clearTokens();
  });

  it('passes page/per_page through to the request', async () => {
    seedTokens();
    let captured: URL | null = null;
    server.use(
      http.get(`${API}/transactions/`, ({ request }) => {
        captured = new URL(request.url);
        return HttpResponse.json({
          items: [],
          total: 0,
          page: 2,
          per_page: 5,
          pages: 0,
        });
      }),
    );

    const { wrapper } = makeWrapper();
    const { useTransactions } = await import('@/hooks/useTransactions');
    const { result } = renderHook(() => useTransactions({ page: 2, per_page: 5 }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(captured).not.toBeNull();
    expect(captured!.searchParams.get('page')).toBe('2');
    expect(captured!.searchParams.get('per_page')).toBe('5');
    expect(captured!.searchParams.get('limit')).toBe('5');
    clearTokens();
  });
});

describe('useCreateTransaction', () => {
  it('invalidates transaction list queries on success', async () => {
    seedTokens();
    const { client, wrapper } = makeWrapper();
    const { useCreateTransaction } = await import('@/hooks/useTransactions');

    // Spy on invalidateQueries to capture every key the mutation invalidates.
    const invalidatedKeys: unknown[][] = [];
    const original = client.invalidateQueries.bind(client);
    client.invalidateQueries = ((arg?: any) => {
      if (arg && Array.isArray(arg.queryKey)) {
        invalidatedKeys.push(arg.queryKey as unknown[]);
      }
      return original(arg);
    }) as typeof client.invalidateQueries;

    const create = renderHook(() => useCreateTransaction(), { wrapper });
    await act(async () => {
      await create.result.current.mutateAsync({
        accountId: 'acct-1',
        amountCents: 999,
        description: 'X',
        transactionDate: '2026-04-15',
      } as any);
    });

    // Mutation success should invalidate transactions lists, budgets and
    // dashboard caches (see useTransactions.ts:99-118).
    const flat = invalidatedKeys.map((k) => k.join('|'));
    expect(flat).toEqual(
      expect.arrayContaining([
        'transactions|list',
        'transactions',
        'budgets',
        'dashboard-summary',
        'category-breakdown',
      ]),
    );
    clearTokens();
  });
});
