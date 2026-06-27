import { defineConfig, devices } from '@playwright/test';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND_DIR = resolve(__dirname, '..', '..', '..', 'frontend');
const PORT = Number(process.env.PW_PREVIEW_PORT || 4173);
const HOST = process.env.PW_PREVIEW_HOST || '127.0.0.1';

/**
 * Playwright config for ad-hoc tests under ./tests. The dependency-free
 * dashboard trace lives in ../scripts/render_trace.mjs and uses the
 * `playwright` library directly — it does NOT use this config.
 *
 * This config is here so that running `npx playwright test` from the
 * harness root works against the same preview server the rest of the
 * baseline targets.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: '../reports/latest/playwright-results.json' }]],
  use: {
    baseURL: `http://${HOST}:${PORT}`,
    trace: 'on',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1350, height: 940 },
  },
  projects: [
    { name: 'chromium-desktop', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: `npm --prefix "${FRONTEND_DIR}" run preview -- --host ${HOST} --port ${PORT} --strictPort`,
    url: `http://${HOST}:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
