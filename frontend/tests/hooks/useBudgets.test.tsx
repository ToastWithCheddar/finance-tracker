/**
 * useBudgets / useCreateBudget / useUpdateBudget / useDeleteBudget —
 * cache invalidation on success.
 *
 * Wraps the hooks in a fresh QueryClient and spies on invalidateQueries to
 * capture the keys each mutation invalidates (cf. useBudgets.ts:74-122).
 */
import { describe, expect, it } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

function spyInvalidations(client: QueryClient): unknown[][] {
  const captured: unknown[][] = [];
  const original = client.invalidateQueries.bind(client);
  client.invalidateQueries = ((arg?: any) => {
    if (arg && Array.isArray(arg.queryKey)) {
      captured.push(arg.queryKey as unknown[]);
    }
    return original(arg);
  }) as typeof client.invalidateQueries;
  return captured;
}

describe('useBudgets', () => {
  it('fetches the budget list via MSW', async () => {
    seedTokens();
    const { wrapper } = makeWrapper();
    const { useBudgets } = await import('@/hooks/useBudgets');
    const { result } = renderHook(() => useBudgets(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.budgets?.length).toBeGreaterThan(0);
    clearTokens();
  });
});

describe('useCreateBudget', () => {
  it('invalidates lists/summary/alerts on success', async () => {
    seedTokens();
    const { client, wrapper } = makeWrapper();
    const captured = spyInvalidations(client);
    const { useCreateBudget } = await import('@/hooks/useBudgets');

    const { result } = renderHook(() => useCreateBudget(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        name: 'New',
        amount_cents: 25000,
        period: 'monthly' as any,
        start_date: '2026-04-01',
      } as any);
    });

    const flat = captured.map((k) => k.join('|'));
    expect(flat).toEqual(
      expect.arrayContaining(['budgets|list', 'budgets|summary', 'budgets|alerts']),
    );
    clearTokens();
  });
});

describe('useUpdateBudget', () => {
  it('invalidates lists/summary/alerts/progress on success', async () => {
    seedTokens();
    const { client, wrapper } = makeWrapper();
    const captured = spyInvalidations(client);
    const { useUpdateBudget } = await import('@/hooks/useBudgets');

    const { result } = renderHook(() => useUpdateBudget(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        budgetId: 'b-1',
        budget: { name: 'Updated' } as any,
      });
    });

    const flat = captured.map((k) => k.join('|'));
    expect(flat).toEqual(
      expect.arrayContaining([
        'budgets|list',
        'budgets|summary',
        'budgets|alerts',
        // updated budget id from MSW handler is the path param echo (b-1)
        'budgets|progress|b-1',
      ]),
    );
    clearTokens();
  });
});

describe('useDeleteBudget', () => {
  it('invalidates lists/summary/alerts on success', async () => {
    seedTokens();
    const { client, wrapper } = makeWrapper();
    const captured = spyInvalidations(client);
    const { useDeleteBudget } = await import('@/hooks/useBudgets');

    const { result } = renderHook(() => useDeleteBudget(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync('b-1');
    });

    const flat = captured.map((k) => k.join('|'));
    expect(flat).toEqual(
      expect.arrayContaining(['budgets|list', 'budgets|summary', 'budgets|alerts']),
    );
    clearTokens();
  });
});
