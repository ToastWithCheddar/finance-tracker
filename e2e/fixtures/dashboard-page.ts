import { Page, expect } from '@playwright/test';

/**
 * Page object for /dashboard, rendered by RealtimeDashboard.tsx.
 */
export class DashboardPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
    await this.waitLoaded();
  }

  async waitLoaded(): Promise<void> {
    // Wait for at least one summary card heading or the main chart container.
    await expect(this.page.locator('main, [role="main"], body')).toBeVisible();
    await this.page.waitForLoadState('networkidle');
  }

  summaryCards() {
    // Summary cards rendered as headings inside the dashboard.
    return this.page.getByRole('heading', {
      name: /balance|income|expense|spending|net|savings/i,
    });
  }

  chart() {
    // Recharts renders an <svg> inside .recharts-wrapper; fall back to any svg
    // larger than a small icon if class is absent.
    return this.page.locator('.recharts-wrapper svg, svg[width][height]').first();
  }

  /** Click the user avatar / sign out control. Locator-flexible because
   *  the menu lives in TopBarExtras.tsx without a testid. */
  async logout(): Promise<void> {
    // Open user menu — we click anything that says "Sign Out" reachable via menu.
    const trigger = this.page.getByRole('button', { name: /account|profile|menu|user/i }).first();
    if (await trigger.isVisible().catch(() => false)) {
      await trigger.click();
    }
    await this.page.getByRole('button', { name: /sign out/i }).click();
    await this.page.waitForURL(/\/login/, { timeout: 10_000 });
  }
}
