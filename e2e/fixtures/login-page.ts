import { Page, expect } from '@playwright/test';

/**
 * Page object for /login. The login form is rendered by
 * frontend/src/components/auth/LoginForm.tsx — selectors here prefer
 * role-based locators because the form has no data-testid attributes.
 */
export class LoginPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/login');
    await expect(
      this.page.getByRole('heading', { name: /sign in/i }),
    ).toBeVisible();
  }

  emailInput() {
    return this.page.getByLabel(/email/i);
  }

  passwordInput() {
    return this.page.getByLabel(/password/i).first();
  }

  submitButton() {
    return this.page.getByRole('button', { name: /^sign in$/i });
  }

  switchToRegisterButton() {
    return this.page.getByRole('button', { name: /sign up/i });
  }

  errorBanner() {
    return this.page.locator('div.bg-red-50, div.text-red-600').first();
  }

  async login(email: string, password: string): Promise<void> {
    await this.emailInput().fill(email);
    await this.passwordInput().fill(password);
    await this.submitButton().click();
    // Successful login navigates to /dashboard (see Login.tsx redirect).
    await this.page.waitForURL(/\/dashboard/, { timeout: 15_000 });
  }
}
