import { Page, expect } from '@playwright/test';

/**
 * Page object for /transactions (Transactions.tsx).
 */
export class TransactionsPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/transactions');
    await expect(
      this.page.getByRole('heading', { name: /^transactions$/i }),
    ).toBeVisible();
  }

  list() {
    // TransactionList renders rows; we accept any list/table semantic.
    return this.page.locator('[data-testid="transaction-list"], table tbody, [role="list"]').first();
  }

  rows() {
    return this.page.locator(
      '[data-testid="transaction-row"], tbody tr, [role="listitem"]',
    );
  }

  searchInput() {
    return this.page.getByPlaceholder(/search/i).first();
  }

  paginationNext() {
    return this.page.getByRole('button', { name: /^next$/i });
  }

  paginationPrev() {
    return this.page.getByRole('button', { name: /^previous$/i });
  }

  addTransactionButton() {
    return this.page.getByRole('button', { name: /add transaction/i });
  }

  async filterBySearch(term: string): Promise<void> {
    const input = this.searchInput();
    await input.fill(term);
    // Debounced — wait for network idle.
    await this.page.waitForLoadState('networkidle');
  }
}
