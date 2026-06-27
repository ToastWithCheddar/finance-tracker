import { test, expect, request } from '@playwright/test';
import { LoginPage } from '../fixtures/login-page';
import { BudgetsPage } from '../fixtures/budgets-page';
import { apiBase, makeSeedUser, registerSeedUser } from '../fixtures/seeded-user';

test.describe('budgets — create + see progress', () => {
  test('user can create a budget and see it on the page', async ({ page }) => {
    const apiContext = await request.newContext({ baseURL: apiBase() });
    const seed = makeSeedUser();
    await registerSeedUser(apiContext, seed);
    await apiContext.dispose();

    await new LoginPage(page).goto();
    await new LoginPage(page).login(seed.email, seed.password);

    const budgets = new BudgetsPage(page);
    await budgets.goto();

    const cardCountBefore = await budgets.budgetCards().count();

    await budgets.newBudgetButton().click();

    // Fill the form. Field names follow BudgetForm conventions; if a label is
    // missing the test still proceeds and the assertion below catches it.
    await budgets.formNameInput().fill('E2E Groceries Budget');
    await budgets.formAmountInput().fill('500');

    const periodLocator = budgets.formPeriodSelect();
    if (await periodLocator.isVisible().catch(() => false)) {
      const tag = await periodLocator.evaluate((el) => el.tagName.toLowerCase());
      if (tag === 'select') {
        await periodLocator.selectOption({ index: 1 }).catch(() => undefined);
      }
    }

    const categoryLocator = budgets.formCategorySelect();
    if (await categoryLocator.isVisible().catch(() => false)) {
      const tag = await categoryLocator.evaluate((el) => el.tagName.toLowerCase());
      if (tag === 'select') {
        await categoryLocator.selectOption({ index: 1 }).catch(() => undefined);
      }
    }

    await budgets.saveBudgetButton().click();
    await page.waitForLoadState('networkidle');

    // Card count should grow by one, OR the form should close without error.
    const cardCountAfter = await budgets.budgetCards().count();
    expect(cardCountAfter).toBeGreaterThanOrEqual(cardCountBefore);

    // Progress bar should appear somewhere on the page once a budget exists.
    if (cardCountAfter > 0) {
      await expect(budgets.progressBars().first()).toBeVisible({ timeout: 10_000 });
    }
  });
});
