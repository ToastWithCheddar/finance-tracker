/**
 * usePlaidLinkToken / useExchangeToken — link-token fetch + exchange flow.
 *
 * usePlaidLinkToken is gated by `enabled` AND a non-null user.id from the
 * auth store, so we seed the auth store before driving the hook.
 */
import { afterEach, describe, expect, it } from 'vitest';
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

afterEach(async () => {
  const { useAuthStore } = await import('@/stores/authStore');
  useAuthStore.setState({ user: null, isAuthenticated: false });
  clearTokens();
});

describe('usePlaidLinkToken', () => {
  it('fetches the link token when enabled and user is present', async () => {
    seedTokens();
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({
      user: { id: 'user-1', email: 't@t.com' } as any,
      isAuthenticated: true,
    });

    const { wrapper } = makeWrapper();
    const { usePlaidLinkToken } = await import('@/hooks/usePlaid');
    const { result } = renderHook(() => usePlaidLinkToken(true), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.link_token).toBe('link-sandbox-token');
  });

  it('stays disabled (no fetch) when enabled=false', async () => {
    seedTokens();
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({
      user: { id: 'user-1', email: 't@t.com' } as any,
      isAuthenticated: true,
    });

    const { wrapper } = makeWrapper();
    const { usePlaidLinkToken } = await import('@/hooks/usePlaid');
    const { result } = renderHook(() => usePlaidLinkToken(false), { wrapper });
    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
  });
});

describe('useExchangeToken', () => {
  it('invalidates accounts/transactions/dashboard caches on success', async () => {
    seedTokens();
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({
      user: { id: 'user-1', email: 't@t.com' } as any,
      isAuthenticated: true,
    });

    const { client, wrapper } = makeWrapper();
    const captured: unknown[][] = [];
    const original = client.invalidateQueries.bind(client);
    client.invalidateQueries = ((arg?: any) => {
      if (arg && Array.isArray(arg.queryKey)) {
        captured.push(arg.queryKey as unknown[]);
      }
      return original(arg);
    }) as typeof client.invalidateQueries;

    const { useExchangeToken } = await import('@/hooks/usePlaid');
    const { result } = renderHook(() => useExchangeToken(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        public_token: 'public-abc',
        metadata: {
          institution: { name: 'X', institution_id: 'ins_1' },
          accounts: [],
        },
      } as any);
    });

    const flat = captured.map((k) => k.join('|'));
    expect(flat).toEqual(
      expect.arrayContaining([
        'accounts',
        'transactions',
        'dashboard',
        'transactions|stats',
      ]),
    );
  });
});
