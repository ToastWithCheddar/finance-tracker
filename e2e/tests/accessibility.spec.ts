import { test, expect, request } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { LoginPage } from '../fixtures/login-page';
import { DashboardPage } from '../fixtures/dashboard-page';
import { apiBase, makeSeedUser, registerSeedUser } from '../fixtures/seeded-user';

/**
 * Baseline a11y scan for finding **FE-A11Y-001**.
 *
 * We assert *no serious or critical* violations on /login (unauthenticated)
 * and /dashboard (authenticated). Lower-severity findings are reported in
 * the HTML report attachment but do not fail the run, so the baseline is
 * actionable without being noisy.
 */
function partition(violations: import('axe-core').Result[]) {
  const blocking = violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  );
  return { blocking, all: violations };
}

test.describe('accessibility — axe baseline (FE-A11Y-001)', () => {
  test('login page has no serious or critical a11y violations', async ({ page }, testInfo) => {
    await new LoginPage(page).goto();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const { blocking, all } = partition(results.violations);
    await testInfo.attach('axe-login.json', {
      body: JSON.stringify(all, null, 2),
      contentType: 'application/json',
    });
    expect(
      blocking,
      `Serious/critical a11y violations: ${blocking.map((v) => v.id).join(', ')}`,
    ).toEqual([]);
  });

  test('dashboard has no serious or critical a11y violations', async ({ page }, testInfo) => {
    const apiContext = await request.newContext({ baseURL: apiBase() });
    const seed = makeSeedUser();
    await registerSeedUser(apiContext, seed);
    await apiContext.dispose();

    await new LoginPage(page).goto();
    await new LoginPage(page).login(seed.email, seed.password);
    await new DashboardPage(page).waitLoaded();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const { blocking, all } = partition(results.violations);
    await testInfo.attach('axe-dashboard.json', {
      body: JSON.stringify(all, null, 2),
      contentType: 'application/json',
    });
    expect(
      blocking,
      `Serious/critical a11y violations: ${blocking.map((v) => v.id).join(', ')}`,
    ).toEqual([]);
  });

  // Day-23 broadening: scan every top-level protected route after login.
  // Each route is a separate test case so failures are localized.
  for (const route of ['/transactions', '/categories', '/budgets', '/goals', '/profile'] as const) {
    test(`${route} has no serious or critical a11y violations`, async ({ page }, testInfo) => {
      const apiContext = await request.newContext({ baseURL: apiBase() });
      const seed = makeSeedUser();
      await registerSeedUser(apiContext, seed);
      await apiContext.dispose();

      await new LoginPage(page).goto();
      await new LoginPage(page).login(seed.email, seed.password);
      await new DashboardPage(page).waitLoaded();

      await page.goto(route);
      // Let the lazy-loaded chunk settle before scanning.
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();
      const { blocking, all } = partition(results.violations);
      await testInfo.attach(`axe${route.replace(/\//g, '-')}.json`, {
        body: JSON.stringify(all, null, 2),
        contentType: 'application/json',
      });
      expect(
        blocking,
        `Serious/critical a11y violations on ${route}: ${blocking.map((v) => v.id).join(', ')}`,
      ).toEqual([]);
    });
  }
});
