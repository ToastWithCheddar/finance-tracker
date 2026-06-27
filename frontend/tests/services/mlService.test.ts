/**
 * mlService — categorize endpoint shape and confidence-threshold guard.
 */
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

describe('mlService', () => {
  it('categorizeTransaction POSTs to /ml/categorize and returns prediction', async () => {
    seedTokens();
    const { mlService } = await import('@/services/mlService');
    const out = await mlService.categorizeTransaction({
      description: 'STARBUCKS',
      amount: 5,
    });
    expect(out.category_id).toBe('cat-food');
    expect(out.confidence).toBeGreaterThan(0.9);
    clearTokens();
  });

  it('autoCategorizeSafe returns null below threshold', async () => {
    seedTokens();
    server.use(
      http.post(`${API}/ml/categorize`, () =>
        HttpResponse.json({
          category_id: 'cat-x',
          confidence: 0.4,
          confidence_level: 'low',
          model_version: 'v1.0',
        }),
      ),
    );
    const { mlService } = await import('@/services/mlService');
    const safe = await mlService.autoCategorizeSafe(
      { description: 'foo', amount: 1 },
      0.8,
    );
    expect(safe).toBeNull();
    clearTokens();
  });

  it('autoCategorizeSafe returns the prediction at/above threshold', async () => {
    seedTokens();
    const { mlService } = await import('@/services/mlService');
    const safe = await mlService.autoCategorizeSafe(
      { description: 'STARBUCKS', amount: 5 },
      0.8,
    );
    expect(safe).not.toBeNull();
    expect(safe?.category_id).toBe('cat-food');
    clearTokens();
  });

  it('isMLServiceAvailable returns true when health is healthy + model_loaded', async () => {
    seedTokens();
    const { mlService } = await import('@/services/mlService');
    expect(await mlService.isMLServiceAvailable()).toBe(true);
    clearTokens();
  });

  it('isMLServiceAvailable returns false when the health endpoint fails', async () => {
    seedTokens();
    server.use(
      http.get(`${API}/ml/health`, () =>
        new HttpResponse(JSON.stringify({ detail: 'down' }), {
          status: 503,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    const { mlService } = await import('@/services/mlService');
    expect(await mlService.isMLServiceAvailable()).toBe(false);
    clearTokens();
  });
});
