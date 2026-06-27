import { test, expect, request } from '@playwright/test';
import { LoginPage } from '../fixtures/login-page';
import { DashboardPage } from '../fixtures/dashboard-page';
import { apiBase, makeSeedUser, registerSeedUser } from '../fixtures/seeded-user';

/**
 * Critical journey: register (via API, since the UI register form takes the
 * same fields and we want a deterministic seed) → email-mock (the dev compose
 * runs GoTrue with autoconfirm enabled, so no inbox interaction is needed) →
 * UI login → UI logout.
 *
 * If your environment requires real email confirmation, override
 * E2E_REQUIRE_EMAIL_CONFIRM=1 — this spec will then xfail with a note.
 */
test.describe('auth — register, login, logout', () => {
  test('user can register, log in, and log out', async ({ page }) => {
    if (process.env.E2E_REQUIRE_EMAIL_CONFIRM === '1') {
      test.fixme(true, 'Email confirmation flow not yet automated (BE-TEST-006)');
    }

    const apiContext = await request.newContext({ baseURL: apiBase() });
    const seed = makeSeedUser();
    const created = await registerSeedUser(apiContext, seed);
    expect(created.email).toBe(seed.email);
    await apiContext.dispose();

    const login = new LoginPage(page);
    await login.goto();
    await login.login(seed.email, seed.password);

    const dashboard = new DashboardPage(page);
    await dashboard.waitLoaded();
    await expect(page).toHaveURL(/\/dashboard/);

    await dashboard.logout();
    await expect(page).toHaveURL(/\/login/);
  });

  test('login with bad credentials surfaces an error banner', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.emailInput().fill('nobody@example.test');
    await login.passwordInput().fill('WrongPass123!');
    await login.submitButton().click();
    await expect(login.errorBanner()).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });
});
