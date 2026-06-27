import { test, expect, request } from '@playwright/test';
import { LoginPage } from '../fixtures/login-page';
import { apiBase, makeSeedUser, registerSeedUser } from '../fixtures/seeded-user';

/**
 * Plaid sandbox link journey. This is gated on PLAID_SANDBOX_CLIENT_ID and
 * PLAID_SANDBOX_SECRET being set in the environment — without them the
 * backend's Plaid client cannot mint a sandbox link_token, and the UI step
 * cannot proceed.
 */
const plaidConfigured =
  !!process.env.PLAID_SANDBOX_CLIENT_ID && !!process.env.PLAID_SANDBOX_SECRET;

test.describe('plaid-link — sandbox connect', () => {
  test.skip(
    !plaidConfigured,
    'PLAID_SANDBOX_CLIENT_ID / PLAID_SANDBOX_SECRET not set; skipping per audit gate',
  );

  test('user can launch Plaid Link and reach the institution selection step', async ({
    page,
  }) => {
    const apiContext = await request.newContext({ baseURL: apiBase() });
    const seed = makeSeedUser();
    await registerSeedUser(apiContext, seed);
    await apiContext.dispose();

    await new LoginPage(page).goto();
    await new LoginPage(page).login(seed.email, seed.password);

    // Most apps trigger Plaid Link from an "Add Account" / "Connect Bank"
    // button on the dashboard or accounts area. We accept any visible CTA.
    const connectCta = page
      .getByRole('button', {
        name: /connect (a )?bank|link account|add account|connect plaid/i,
      })
      .first();
    await expect(connectCta).toBeVisible({ timeout: 15_000 });
    await connectCta.click();

    // Plaid Link mounts an iframe sandboxed at https://cdn.plaid.com/link/...
    const plaidFrame = page.frameLocator('iframe[src*="plaid.com"]').first();
    await expect(
      plaidFrame.getByText(/select your bank|search for your bank|continue/i).first(),
    ).toBeVisible({ timeout: 20_000 });
  });
});
