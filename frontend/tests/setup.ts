import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './msw/server';

// ---------------------------------------------------------------------------
// MSW lifecycle
// ---------------------------------------------------------------------------
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  // Wipe storage between tests so persisted Zustand state doesn't leak.
  try {
    window.localStorage.clear();
    window.sessionStorage.clear();
  } catch {
    /* happy-dom may not have storage in some edge cases */
  }
  vi.clearAllMocks();
});

afterAll(() => {
  server.close();
});

// ---------------------------------------------------------------------------
// Browser shims for the happy-dom + Vitest environment. happy-dom provides
// localStorage/sessionStorage already,
// but we still stub the observer APIs and matchMedia which the app touches.
// ---------------------------------------------------------------------------
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

class IntersectionObserverStub {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds: ReadonlyArray<number> = [];
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

// @ts-expect-error -- assigning stub to global in happy-dom env
globalThis.ResizeObserver = ResizeObserverStub;
// @ts-expect-error -- assigning stub to global in happy-dom env
globalThis.IntersectionObserver = IntersectionObserverStub;

if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

if (!window.scrollTo) {
  Object.defineProperty(window, 'scrollTo', {
    writable: true,
    value: vi.fn(),
  });
}

// ---------------------------------------------------------------------------
// Module mocks for toast libraries that are not installed in this audit
// workspace. The real frontend depends on `sonner` and `react-hot-toast`;
// rather than dual-installing them, expose minimal stubs so source modules
// that import them don't ESM-resolve to a missing module under Vitest.
// ---------------------------------------------------------------------------
vi.mock('sonner', () => {
  const noop = vi.fn();
  return {
    toast: Object.assign(noop, {
      success: noop,
      error: noop,
      info: noop,
      warning: noop,
      message: noop,
      dismiss: noop,
    }),
    Toaster: () => null,
  };
});

vi.mock('react-hot-toast', () => {
  const noop = vi.fn();
  return {
    toast: Object.assign(noop, {
      success: noop,
      error: noop,
      loading: noop,
      dismiss: noop,
    }),
    default: { success: noop, error: noop },
    Toaster: () => null,
  };
});

// Silence the per-request token-prefix console.log noise from api.ts:77,79
// during tests. We don't want to mask real errors, so leave error/warn alone.
const originalLog = console.log;
console.log = (...args: unknown[]) => {
  const first = args[0];
  if (typeof first === 'string' && (first.startsWith('🔐') || first.startsWith('🚫'))) {
    return;
  }
  originalLog(...args);
};
