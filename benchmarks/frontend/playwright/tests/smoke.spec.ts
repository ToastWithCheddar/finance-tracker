import { test, expect } from '@playwright/test';

/**
 * Minimal smoke that the preview server boots and serves the SPA shell.
 * Real perf measurement lives in ../scripts/render_trace.mjs; this exists
 * so `npx playwright test` from the harness root has at least one test.
 */
test('preview serves an HTML document', async ({ page }) => {
  const response = await page.goto('/');
  expect(response, 'navigation response').not.toBeNull();
  expect(response!.status(), 'http status').toBeLessThan(400);
  await expect(page.locator('html')).toBeVisible();
});
