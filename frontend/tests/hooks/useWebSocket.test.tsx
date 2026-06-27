/**
 * useWebSocket — connection lifecycle.
 *
 * Replaces the global WebSocket constructor with a controllable stub so we
 * can drive open/close events deterministically. Reconnect is scheduled via
 * `setTimeout(_, 5000)` (useWebSocket.ts:256, 291); we use fake timers to
 * advance the clock instead of waiting in real time.
 *
 * FE-SEC-001: the current implementation puts the access token in the
 * WebSocket URL query string (`?token=${accessToken}`). Tokens-in-URL gets
 * logged by proxies and shows up in browser history — the it.skip below
 * pins the gap until the implementation switches to a Sec-WebSocket-Protocol
 * header or a per-connection handshake message.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

// ---- WebSocket stub --------------------------------------------------------
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;
  url: string;
  readyState = 0;
  onopen: ((ev: any) => void) | null = null;
  onclose: ((ev: any) => void) | null = null;
  onerror: ((ev: any) => void) | null = null;
  onmessage: ((ev: any) => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ wasClean: true, code: 1000, reason: 'normal' });
  }
  // helpers
  triggerOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({});
  }
  triggerClose(wasClean = false) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ wasClean, code: wasClean ? 1000 : 1006, reason: '' });
  }
}

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

beforeEach(() => {
  MockWebSocket.instances.length = 0;
  // Backfill calls that happen on connect — answer them so they don't 404.
  server.use(
    http.get(`${API}/transactions/`, () =>
      HttpResponse.json({ items: [], total: 0, page: 1, per_page: 20, pages: 0 }),
    ),
    http.get(`${API}/notifications`, () =>
      HttpResponse.json({ notifications: [], total: 0 }),
    ),
  );
  // jsdom marks `globalThis.WebSocket` as a non-writable accessor, so a
  // direct assignment throws. Use vi.stubGlobal which goes through
  // Object.defineProperty under the hood and works in both happy-dom and
  // jsdom.
  vi.stubGlobal('WebSocket', MockWebSocket);
});

afterEach(async () => {
  clearTokens();
  const { useAuthStore } = await import('@/stores/authStore');
  useAuthStore.setState({ user: null, isAuthenticated: false });
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useWebSocket', () => {
  it('does not open a socket when unauthenticated', async () => {
    // Unauthenticated path is the strongest "do not connect" guard in
    // useWebSocket.ts (the autoConnect=false branch happens in a sibling
    // effect that runs *after* the connection effect has already opened
    // a socket — see useWebSocket.ts:53-78 vs 98-319).
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({ user: null, isAuthenticated: false });

    const { wrapper } = makeWrapper();
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    expect(MockWebSocket.instances).toHaveLength(0);
    expect(result.current.isConnected).toBe(false);
  });

  it('opens a socket and reports connected on open', async () => {
    seedTokens();
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({
      user: { id: 'user-1', email: 't@t.com' } as any,
      isAuthenticated: true,
    });

    const { wrapper } = makeWrapper();
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const { result } = renderHook(() => useWebSocket(), { wrapper });

    await waitFor(() => expect(MockWebSocket.instances.length).toBe(1));
    act(() => {
      MockWebSocket.instances[0].triggerOpen();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));
  });

  it('reconnects after a non-clean close (after 5s)', async () => {
    vi.useFakeTimers();
    seedTokens();
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({
      user: { id: 'user-1', email: 't@t.com' } as any,
      isAuthenticated: true,
    });

    const { wrapper } = makeWrapper();
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    renderHook(() => useWebSocket(), { wrapper });

    // Wait for initial socket creation under fake timers
    await vi.waitFor(() => expect(MockWebSocket.instances.length).toBe(1));
    act(() => {
      MockWebSocket.instances[0].triggerOpen();
    });
    act(() => {
      MockWebSocket.instances[0].triggerClose(false);
    });

    // Advance fake clock past the 5s reconnect delay
    act(() => {
      vi.advanceTimersByTime(5_001);
    });
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2);
  });

  // FE-SEC-001: the access token is currently embedded in the URL query.
  // Once the impl switches to Sec-WebSocket-Protocol or a handshake message,
  // remove `.skip` and assert the URL no longer contains the token.
  it.skip('FE-SEC-001: access token is NOT included in the WebSocket URL', async () => {
    seedTokens();
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.setState({
      user: { id: 'user-1', email: 't@t.com' } as any,
      isAuthenticated: true,
    });

    const { wrapper } = makeWrapper();
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    renderHook(() => useWebSocket(), { wrapper });
    await waitFor(() => expect(MockWebSocket.instances.length).toBe(1));
    expect(MockWebSocket.instances[0].url).not.toMatch(/[?&]token=/);
  });
});
