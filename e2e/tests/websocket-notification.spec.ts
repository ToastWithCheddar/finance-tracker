import { test, expect, request } from '@playwright/test';
import { LoginPage } from '../fixtures/login-page';
import { DashboardPage } from '../fixtures/dashboard-page';
import { apiBase, makeSeedUser, registerSeedUser } from '../fixtures/seeded-user';

/**
 * Open dashboard, simulate a server-pushed notification, expect it to surface
 * in the realtime UI.
 *
 * The audit notes that the backend does not currently expose a dev-only
 * `/api/internal/test-notify` hook (finding **BE-TEST-006**). If the endpoint
 * returns 404 we mark the test fixme so the suite stays green and the gap is
 * tracked.
 */
test.describe('websocket — notification round-trip', () => {
  test('a server-emitted notification renders on the dashboard', async ({ page }) => {
    const apiContext = await request.newContext({ baseURL: apiBase() });
    const seed = makeSeedUser();
    await registerSeedUser(apiContext, seed);

    // Probe for the test hook before doing UI work.
    const probe = await apiContext.post(`${apiBase()}/internal/test-notify`, {
      data: { type: 'ping', message: 'probe' },
      failOnStatusCode: false,
    });
    const hookExists = probe.status() !== 404;
    test.fixme(
      !hookExists,
      'Backend test-notify hook missing (finding BE-TEST-006); cannot inject WS event from outside.',
    );

    // Login to get an auth token for the actual notify call.
    const loginResp = await apiContext.post(`${apiBase()}/auth/login`, {
      data: { email: seed.email, password: seed.password },
    });
    const loginBody = await loginResp.json().catch(() => ({}));
    const token: string | undefined =
      loginBody?.access_token ?? loginBody?.session?.access_token;

    await new LoginPage(page).goto();
    await new LoginPage(page).login(seed.email, seed.password);

    const dashboard = new DashboardPage(page);
    await dashboard.waitLoaded();

    // Inject a notification via the (assumed) test hook.
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const notifyResp = await apiContext.post(`${apiBase()}/internal/test-notify`, {
      headers,
      data: {
        type: 'transaction_created',
        title: 'E2E Test Notification',
        message: 'Hello from Playwright',
      },
    });
    expect(notifyResp.ok()).toBeTruthy();

    // Toast / banner / notification list — accept any of them.
    const notif = page
      .getByText(/E2E Test Notification|Hello from Playwright/i)
      .first();
    await expect(notif).toBeVisible({ timeout: 15_000 });

    await apiContext.dispose();
  });
});
