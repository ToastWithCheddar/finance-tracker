import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for the finance-tracker critical-journey suite.
 *
 * Pre-condition: the dev stack must already be up via `docker compose up -d`
 * (see /docker-compose.yml at repo root). We deliberately do NOT use
 * Playwright's `webServer` because the not-yet-authored compose.test.yml
 * referenced in docs/audit/improvement-sections/B-testing.md is the future
 * test stack — for now the user runs against the running dev stack.
 *
 * Override the base URL with E2E_BASE_URL (default: http://localhost — the
 * nginx reverse proxy in docker-compose.yml).
 */
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 14'] },
    },
  ],
});
