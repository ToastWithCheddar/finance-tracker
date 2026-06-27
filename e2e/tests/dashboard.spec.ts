import { test, expect, request } from '@playwright/test';
import { LoginPage } from '../fixtures/login-page';
import { DashboardPage } from '../fixtures/dashboard-page';
import { apiBase, makeSeedUser, registerSeedUser } from '../fixtures/seeded-user';

test.describe('dashboard — summary cards + chart', () => {
  test('summary cards render and at least one chart is visible', async ({ page }) => {
    const apiContext = await request.newContext({ baseURL: apiBase() });
    const seed = makeSeedUser();
    await registerSeedUser(apiContext, seed);
    await apiContext.dispose();

    await new LoginPage(page).goto();
    await new LoginPage(page).login(seed.email, seed.password);

    const dashboard = new DashboardPage(page);
    await dashboard.waitLoaded();

    // Expect at least one summary heading.
    const cards = dashboard.summaryCards();
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });

    // Recharts wrapper or any sizable inline svg.
    const chart = dashboard.chart();
    await expect(chart).toBeVisible({ timeout: 15_000 });
  });
});
