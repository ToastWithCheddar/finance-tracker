#!/usr/bin/env node
/**
 * Playwright dashboard trace for finance-tracker frontend.
 *
 * - Spawns `npm run preview` in ../../frontend on port 4173.
 * - Launches Chromium, navigates to /dashboard (the route falls back to
 *   /login for unauthenticated users — we measure both as a smoke).
 * - Captures FCP, LCP, TBT-ish (via long-task observer) plus a screenshot
 *   and a Playwright trace zip.
 * - Output JSON path comes from $TRACE_OUTPUT, defaulting to
 *   reports/latest/dashboard-trace.json.
 *
 * Standalone of the @playwright/test runner — it's a plain script using
 * the `playwright` library so it can be invoked from capture_baseline.sh
 * without `npx playwright test`.
 */

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';
import net from 'node:net';

const __dirname = dirname(fileURLToPath(import.meta.url));
const HARNESS_DIR = resolve(__dirname, '..');
const FRONTEND_DIR = resolve(HARNESS_DIR, '..', '..', 'frontend');
const DIST_DIR = resolve(FRONTEND_DIR, 'dist');

const PORT = Number(process.env.TRACE_PREVIEW_PORT || 4173);
const HOST = process.env.TRACE_PREVIEW_HOST || '127.0.0.1';
const ROUTES = ['/login', '/dashboard'];
const OUTPUT_PATH = process.env.TRACE_OUTPUT
  || resolve(HARNESS_DIR, 'reports', 'latest', 'dashboard-trace.json');

if (!existsSync(DIST_DIR)) {
  console.error(`render_trace: ${DIST_DIR} not found. Build the frontend first.`);
  process.exit(1);
}

function waitForPort(host, port, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolveP, rejectP) => {
    const tick = () => {
      const sock = net.createConnection({ host, port });
      sock.once('connect', () => { sock.destroy(); resolveP(); });
      sock.once('error', () => {
        sock.destroy();
        if (Date.now() > deadline) rejectP(new Error(`port ${host}:${port} not ready`));
        else setTimeout(tick, 250);
      });
    };
    tick();
  });
}

async function measureRoute(page, url) {
  const navStart = Date.now();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30_000 });

  // Inject observers, then wait briefly for LCP / long-tasks to settle.
  await page.evaluate(() => {
    // @ts-ignore browser globals
    window.__perf = { lcp: null, longTasks: [] };
    try {
      // @ts-ignore
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        if (last) window.__perf.lcp = last.startTime;
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch {}
    try {
      // @ts-ignore
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          window.__perf.longTasks.push({ start: entry.startTime, duration: entry.duration });
        }
      }).observe({ type: 'longtask', buffered: true });
    } catch {}
  });

  await sleep(2000);

  const metrics = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const paints = performance.getEntriesByType('paint');
    const fcp = paints.find((p) => p.name === 'first-contentful-paint')?.startTime ?? null;
    // TBT approximation: sum of (longTask.duration - 50) for tasks within first 5s.
    // @ts-ignore
    const longTasks = (window.__perf?.longTasks || []).filter((t) => t.start < 5000);
    const tbt = longTasks.reduce((acc, t) => acc + Math.max(0, t.duration - 50), 0);
    return {
      // @ts-ignore
      lcpMs: window.__perf?.lcp ?? null,
      fcpMs: fcp,
      tbtMs: tbt,
      longTaskCount: longTasks.length,
      navigation: nav ? {
        domContentLoaded: nav.domContentLoadedEventEnd,
        loadEventEnd: nav.loadEventEnd,
        transferSize: nav.transferSize,
        encodedBodySize: nav.encodedBodySize,
        decodedBodySize: nav.decodedBodySize,
      } : null,
    };
  });

  return { url, wallClockMs: Date.now() - navStart, ...metrics };
}

async function main() {
  console.log(`render_trace: starting preview on ${HOST}:${PORT}`);
  const previewProc = spawn(
    'npm',
    ['--prefix', FRONTEND_DIR, 'run', 'preview', '--', '--host', HOST, '--port', String(PORT), '--strictPort'],
    { stdio: 'inherit', env: { ...process.env } },
  );

  let exitCode = 0;
  try {
    await waitForPort(HOST, PORT, 60_000);

    const browser = await chromium.launch({ args: ['--no-sandbox'] });
    const context = await browser.newContext({ viewport: { width: 1350, height: 940 } });
    await context.tracing.start({ screenshots: true, snapshots: true });
    const page = await context.newPage();

    const results = [];
    for (const route of ROUTES) {
      const url = `http://${HOST}:${PORT}${route}`;
      try {
        const r = await measureRoute(page, url);
        results.push(r);
        const screenshotPath = OUTPUT_PATH.replace(/\.json$/, `${route.replace(/\//g, '_')}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
      } catch (err) {
        results.push({ url, error: String(err) });
      }
    }

    const tracePath = OUTPUT_PATH.replace(/\.json$/, '-trace.zip');
    mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
    await context.tracing.stop({ path: tracePath });
    await browser.close();

    const out = {
      generatedAt: new Date().toISOString(),
      previewUrl: `http://${HOST}:${PORT}`,
      tracePath,
      results,
    };
    writeFileSync(OUTPUT_PATH, JSON.stringify(out, null, 2));
    console.log(`render_trace: wrote ${OUTPUT_PATH}`);
  } catch (err) {
    console.error('render_trace: failed', err);
    exitCode = 1;
  } finally {
    previewProc.kill('SIGTERM');
    await sleep(500);
    if (!previewProc.killed) previewProc.kill('SIGKILL');
  }
  process.exit(exitCode);
}

main();
