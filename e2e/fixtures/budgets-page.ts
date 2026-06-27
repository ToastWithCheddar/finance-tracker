import { Page, expect } from '@playwright/test';

/**
 * Page object for /budgets (Budgets.tsx).
 */
export class BudgetsPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/budgets');
    await expect(
      this.page.getByRole('heading', { name: /budget management/i }),
    ).toBeVisible();
  }

  newBudgetButton() {
    return this.page
      .getByRole('button', { name: /new budget|create budget|\+ budget|add budget/i })
      .first();
  }

  formNameInput() {
    return this.page.getByLabel(/name/i).first();
  }

  formAmountInput() {
    return this.page.getByLabel(/amount|limit/i).first();
  }

  formCategorySelect() {
    return this.page.getByLabel(/category/i).first();
  }

  formPeriodSelect() {
    return this.page.getByLabel(/period|frequency/i).first();
  }

  saveBudgetButton() {
    return this.page.getByRole('button', { name: /^(save|create|submit)$/i }).first();
  }

  budgetCards() {
    return this.page.locator(
      '[data-testid="budget-card"], [data-testid="budget-card-container"]',
    );
  }

  progressBars() {
    return this.page.locator('[role="progressbar"], [data-testid="budget-progress"]');
  }
}
