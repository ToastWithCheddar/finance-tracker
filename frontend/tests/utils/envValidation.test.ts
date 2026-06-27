/**
 * utils/envValidation.ts — strict-mode validation contract.
 *
 * FE-PR-003: getConfig() falls back to a literal localhost URL when
 * VITE_API_URL is not set. That hard-coded fallback means a misconfigured
 * production build silently points at localhost instead of failing fast.
 * The xfail test below documents the gap; flip to `it()` once the fallback
 * is removed (or the validator throws in non-DEV builds).
 */
import { describe, expect, it } from 'vitest';

describe('envValidator', () => {
  it('reports valid when VITE_API_URL is a well-formed URL', async () => {
    const { envValidator } = await import('@/utils/envValidation');
    const result = envValidator.validateEnvironment();
    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it('getConfig returns the configured URL', async () => {
    const { envValidator } = await import('@/utils/envValidation');
    const cfg = envValidator.getConfig();
    expect(cfg.VITE_API_URL).toBe('http://localhost:8000/api');
    expect(cfg.VITE_APP_NAME).toBeDefined();
  });

  // FE-PR-003: localhost fallback present in getConfig — should be removed.
  it.fails(
    'FE-PR-003: getConfig should NOT silently fall back to localhost when unset',
    async () => {
      // We can't unset the env var that vitest.config injects at runtime, so
      // we assert the *source* contract: the OR-fallback string must not be
      // a hard-coded localhost. Today it is — hence xfail.
      const src = await import('@/utils/envValidation?raw' as string).catch(() => null);
      // If the raw-import isn't supported, this still fails on the next line.
      const text = (src as any)?.default ?? '';
      expect(text).not.toMatch(/http:\/\/localhost:8000\/api/);
    },
  );
});
