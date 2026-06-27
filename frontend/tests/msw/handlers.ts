import { http, HttpResponse } from 'msw';

// Base URL aligns with frontend/src/utils/envValidation.ts:78
const API = 'http://localhost:8000/api';

/**
 * Baseline /api/* handlers shaped to match the real backend (snake_case,
 * see backend/app/schemas/auth.py — TokenResponse + AuthResponse).
 *
 * Individual tests may call `server.use(...)` to override these per-test.
 */
export const handlers = [
  // ---- Auth -------------------------------------------------------------
  http.post(`${API}/auth/login`, async () => {
    return HttpResponse.json({
      user: {
        id: 'user-1',
        email: 'test@example.com',
        full_name: 'Test User',
      },
      tokens: {
        access_token: 'access-token-initial',
        refresh_token: 'refresh-token-initial',
        token_type: 'bearer',
        expires_in: 1800,
      },
    });
  }),

  http.post(`${API}/auth/refresh`, async () => {
    // NOTE: The real backend returns snake_case (TokenResponse). The current
    // api.ts:309-314 reads camelCase — that mismatch is FE-SEC-003.
    return HttpResponse.json({
      access_token: 'access-token-refreshed',
      refresh_token: 'refresh-token-refreshed',
      token_type: 'bearer',
      expires_in: 1800,
    });
  }),

  http.get(`${API}/auth/me`, async () => {
    return HttpResponse.json({
      id: 'user-1',
      email: 'test@example.com',
      full_name: 'Test User',
    });
  }),

  http.post(`${API}/auth/logout`, async () => HttpResponse.json({ ok: true })),

  // ---- Transactions -----------------------------------------------------
  http.get(`${API}/transactions`, async () => {
    return HttpResponse.json({
      items: [
        {
          id: 'tx-1',
          user_id: 'user-1',
          account_id: 'acct-1',
          category_id: 'cat-1',
          amount_cents: 1234,
          currency: 'USD',
          description: 'Coffee',
          transaction_date: '2026-04-01',
          status: 'posted',
          is_transfer: false,
          tags: [],
          created_at: '2026-04-01T10:00:00Z',
          updated_at: '2026-04-01T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      per_page: 25,
      pages: 1,
    });
  }),

  http.post(`${API}/transactions/`, async () =>
    HttpResponse.json({
      id: 'tx-new',
      user_id: 'user-1',
      account_id: 'acct-1',
      category_id: 'cat-1',
      amount_cents: 500,
      currency: 'USD',
      description: 'New tx',
      transaction_date: '2026-04-15',
      status: 'posted',
      is_transfer: false,
      tags: [],
      created_at: '2026-04-15T10:00:00Z',
      updated_at: '2026-04-15T10:00:00Z',
    }),
  ),

  // ---- Budgets ----------------------------------------------------------
  http.get(`${API}/budgets`, async () =>
    HttpResponse.json({
      budgets: [
        {
          id: 'b-1',
          user_id: 'user-1',
          name: 'Groceries',
          amount_cents: 50000,
          period: 'monthly',
          start_date: '2026-04-01',
          alert_threshold: 80,
          is_active: true,
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-01T00:00:00Z',
        },
      ],
      summary: {
        total_budgets: 1,
        active_budgets: 1,
        total_budgeted_cents: 50000,
        total_spent_cents: 12000,
        total_remaining_cents: 38000,
        over_budget_count: 0,
        alert_count: 0,
      },
      alerts: [],
    }),
  ),

  http.post(`${API}/budgets`, async () =>
    HttpResponse.json({
      id: 'b-new',
      user_id: 'user-1',
      name: 'New',
      amount_cents: 25000,
      period: 'monthly',
      start_date: '2026-04-01',
      alert_threshold: 80,
      is_active: true,
      created_at: '2026-04-01T00:00:00Z',
      updated_at: '2026-04-01T00:00:00Z',
    }),
  ),

  http.put(`${API}/budgets/:id`, async ({ params }) =>
    HttpResponse.json({
      id: params.id,
      user_id: 'user-1',
      name: 'Updated',
      amount_cents: 30000,
      period: 'monthly',
      start_date: '2026-04-01',
      alert_threshold: 80,
      is_active: true,
      created_at: '2026-04-01T00:00:00Z',
      updated_at: '2026-04-02T00:00:00Z',
    }),
  ),

  http.delete(`${API}/budgets/:id`, async () =>
    HttpResponse.json({ message: 'deleted' }),
  ),

  // ---- Accounts ---------------------------------------------------------
  http.get(`${API}/accounts/`, async () =>
    HttpResponse.json([
      {
        id: 'acct-1',
        user_id: 'user-1',
        name: 'Checking',
        account_type: 'checking',
        balance_cents: 100000,
        currency: 'USD',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-04-01T00:00:00Z',
      },
    ]),
  ),

  http.post(`${API}/accounts/`, async () =>
    HttpResponse.json({
      id: 'acct-new',
      user_id: 'user-1',
      name: 'New Account',
      account_type: 'savings',
      balance_cents: 0,
      currency: 'USD',
      is_active: true,
      created_at: '2026-04-15T00:00:00Z',
      updated_at: '2026-04-15T00:00:00Z',
    }),
  ),

  // ---- Plaid ------------------------------------------------------------
  http.post(`${API}/accounts/plaid/link-token`, async () =>
    HttpResponse.json({
      success: true,
      link_token: 'link-sandbox-token',
      expiration: '2026-04-15T11:00:00Z',
      request_id: 'req-1',
      environment: 'sandbox',
    }),
  ),

  http.post(`${API}/accounts/plaid/exchange-token`, async () =>
    HttpResponse.json({
      success: true,
      message: 'Connected',
      data: {
        accounts: [
          {
            id: 'acct-2',
            name: 'Plaid Checking',
            account_type: 'checking',
            balance_cents: 50000,
            currency: 'USD',
            plaid_account_id: 'plaid-1',
            plaid_item_id: 'item-1',
            sync_status: 'idle',
            connection_health: 'healthy',
            created_at: '2026-04-15T00:00:00Z',
            updated_at: '2026-04-15T00:00:00Z',
          },
        ],
        accounts_created: 1,
        institution: 'Test Bank',
      },
    }),
  ),

  // ---- ML ---------------------------------------------------------------
  http.post(`${API}/ml/categorize`, async () =>
    HttpResponse.json({
      category_id: 'cat-food',
      confidence: 0.92,
      confidence_level: 'high',
      model_version: 'v1.0',
      all_similarities: { 'cat-food': 0.92, 'cat-other': 0.1 },
    }),
  ),

  http.get(`${API}/ml/health`, async () =>
    HttpResponse.json({
      status: 'healthy',
      model_loaded: true,
      prototypes_loaded: true,
      categories_count: 12,
      model_version: 'v1.0',
    }),
  ),

  // ---- Dashboard --------------------------------------------------------
  http.get(`${API}/dashboard/summary`, async () =>
    HttpResponse.json({
      net_worth: 250000,
      total_liquid: 100000,
      total_debt: 0,
      total_investment: 150000,
      financial_health_score: 85,
      financial_health_grade: 'A',
      account_count: 3,
      recent_transactions: 10,
      recommendations: [],
    }),
  ),

  http.get(`${API}/dashboard/net-worth-trend`, async () =>
    HttpResponse.json([
      { date: '2026-01-01', net_worth: 200000 },
      { date: '2026-04-01', net_worth: 250000 },
    ]),
  ),

  // ---- Budgets analytics ------------------------------------------------
  http.get(`${API}/budgets/analytics/summary`, async () =>
    HttpResponse.json({
      total_budgets: 1,
      active_budgets: 1,
      total_budgeted_cents: 50000,
      total_spent_cents: 12000,
      total_remaining_cents: 38000,
      over_budget_count: 0,
      alert_count: 0,
    }),
  ),

  http.get(`${API}/budgets/analytics/alerts`, async () => HttpResponse.json([])),

  // ---- Notifications (used by useWebSocket backfill) --------------------
  http.get(`${API}/notifications`, async () =>
    HttpResponse.json({ notifications: [], total: 0 }),
  ),

  // ---- Plaid connection status -----------------------------------------
  http.get(`${API}/accounts/connection-status`, async () =>
    HttpResponse.json({ total_connections: 0, accounts: [] }),
  ),
];
