/**
 * budgetService — request shape + helper logic.
 * Covers the CRUD wrappers around apiClient and the pure helpers
 * (calculateUtilization, getBudgetStatus, isExceeded, ...).
 */
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../msw/server';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

const API = 'http://localhost:8000/api';

describe('budgetService', () => {
  it('getBudgets sends filter params snake_cased', async () => {
    seedTokens();
    let captured: URL | null = null;
    server.use(
      http.get(`${API}/budgets`, ({ request }) => {
        captured = new URL(request.url);
        return HttpResponse.json({
          budgets: [],
          summary: {
            total_budgets: 0,
            active_budgets: 0,
            total_budgeted_cents: 0,
            total_spent_cents: 0,
            total_remaining_cents: 0,
            over_budget_count: 0,
            alert_count: 0,
          },
          alerts: [],
        });
      }),
    );

    const { budgetService } = await import('@/services/budgetService');
    await budgetService.getBudgets({
      category_id: 'cat-1',
      is_active: true,
      over_budget: false,
      limit: 25,
    });

    expect(captured).not.toBeNull();
    const params = captured!.searchParams;
    expect(params.get('category_id')).toBe('cat-1');
    expect(params.get('is_active')).toBe('true');
    expect(params.get('limit')).toBe('25');
    clearTokens();
  });

  it('createBudget POSTs to /budgets and returns the created entity', async () => {
    seedTokens();
    const { budgetService } = await import('@/services/budgetService');
    const created = await budgetService.createBudget({
      name: 'New',
      amount_cents: 25000,
      period: 'monthly' as any,
      start_date: '2026-04-01',
    });
    expect(created.id).toBe('b-new');
    expect(created.name).toBe('New');
    clearTokens();
  });

  it('updateBudget PUTs to /budgets/:id', async () => {
    seedTokens();
    const { budgetService } = await import('@/services/budgetService');
    const updated = await budgetService.updateBudget('b-1', { name: 'Updated' });
    expect(updated.id).toBe('b-1');
    expect(updated.name).toBe('Updated');
    clearTokens();
  });

  it('deleteBudget DELETEs to /budgets/:id', async () => {
    seedTokens();
    const { budgetService } = await import('@/services/budgetService');
    const out = await budgetService.deleteBudget('b-1');
    expect(out.message).toBe('deleted');
    clearTokens();
  });

  it('getBudgets surfaces network errors as thrown errors', async () => {
    seedTokens();
    server.use(
      http.get(`${API}/budgets`, () =>
        new HttpResponse(JSON.stringify({ detail: 'boom' }), {
          status: 500,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    const { budgetService } = await import('@/services/budgetService');
    await expect(budgetService.getBudgets()).rejects.toBeDefined();
    clearTokens();
  });

  // ----- Pure helpers --------------------------------------------------
  it('calculateUtilization returns rounded percentage', async () => {
    const { budgetService } = await import('@/services/budgetService');
    expect(budgetService.calculateUtilization(10000, 5000)).toBe(50);
    expect(budgetService.calculateUtilization(0, 100)).toBe(0);
    expect(budgetService.calculateUtilization(10000, 12345)).toBe(123);
  });

  it('getBudgetStatusDetailed maps thresholds correctly', async () => {
    const { budgetService } = await import('@/services/budgetService');
    expect(budgetService.getBudgetStatusDetailed(100, 50)).toBe('good');
    expect(budgetService.getBudgetStatusDetailed(100, 85)).toBe('warning');
    expect(budgetService.getBudgetStatusDetailed(100, 150)).toBe('exceeded');
  });

  it('getBudgetStatus considers BudgetUsage flags', async () => {
    const { budgetService } = await import('@/services/budgetService');
    expect(budgetService.getBudgetStatus(undefined)).toBe('unknown');
    expect(
      budgetService.getBudgetStatus({
        budget_id: 'x',
        spent_cents: 0,
        remaining_cents: 100,
        percentage_used: 50,
        is_over_budget: false,
      }),
    ).toBe('on-track');
    expect(
      budgetService.getBudgetStatus({
        budget_id: 'x',
        spent_cents: 0,
        remaining_cents: 0,
        percentage_used: 95,
        is_over_budget: false,
      }),
    ).toBe('warning');
    expect(
      budgetService.getBudgetStatus({
        budget_id: 'x',
        spent_cents: 0,
        remaining_cents: 0,
        percentage_used: 110,
        is_over_budget: true,
      }),
    ).toBe('over-budget');
  });
});
