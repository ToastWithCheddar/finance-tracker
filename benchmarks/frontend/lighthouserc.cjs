/**
 * Lighthouse CI configuration for finance-tracker frontend.
 *
 * - Targets the Vite preview server (`npm run preview` in ../../frontend),
 *   so it benchmarks the actual production-mode build.
 * - 3 runs per URL; LHCI uses the median.
 * - Desktop form factor by default; set LHCI_FORM_FACTOR=mobile to switch.
 * - Budgets are assertions but reported as warnings during the foundation
 *   wave (off → warn). Flip to "error" once a stable baseline is captured.
 */

const path = require('path');

const FORM_FACTOR = process.env.LHCI_FORM_FACTOR === 'mobile' ? 'mobile' : 'desktop';
const PREVIEW_PORT = process.env.LHCI_PREVIEW_PORT || '4173';
const PREVIEW_HOST = process.env.LHCI_PREVIEW_HOST || '127.0.0.1';
const FRONTEND_DIR = path.resolve(__dirname, '..', '..', 'frontend');

const desktopSettings = {
  preset: 'desktop',
  formFactor: 'desktop',
  screenEmulation: {
    mobile: false,
    width: 1350,
    height: 940,
    deviceScaleFactor: 1,
    disabled: false,
  },
  throttling: {
    rttMs: 40,
    throughputKbps: 10240,
    cpuSlowdownMultiplier: 1,
    requestLatencyMs: 0,
    downloadThroughputKbps: 0,
    uploadThroughputKbps: 0,
  },
  throttlingMethod: 'simulate',
};

const mobileSettings = {
  formFactor: 'mobile',
  screenEmulation: {
    mobile: true,
    width: 412,
    height: 823,
    deviceScaleFactor: 1.75,
    disabled: false,
  },
  throttling: {
    rttMs: 150,
    throughputKbps: 1638.4,
    cpuSlowdownMultiplier: 4,
    requestLatencyMs: 0,
    downloadThroughputKbps: 0,
    uploadThroughputKbps: 0,
  },
  throttlingMethod: 'simulate',
};

module.exports = {
  ci: {
    collect: {
      // LHCI will spawn this command, wait for the URL, run Lighthouse, then kill it.
      startServerCommand: `npm --prefix "${FRONTEND_DIR}" run preview -- --host ${PREVIEW_HOST} --port ${PREVIEW_PORT} --strictPort`,
      startServerReadyPattern: 'Local:',
      startServerReadyTimeout: 60_000,
      url: [
        `http://${PREVIEW_HOST}:${PREVIEW_PORT}/login`,
        `http://${PREVIEW_HOST}:${PREVIEW_PORT}/dashboard`,
      ],
      numberOfRuns: 3,
      settings: {
        chromeFlags: '--no-sandbox --headless=new --disable-gpu --disable-dev-shm-usage',
        ...(FORM_FACTOR === 'mobile' ? mobileSettings : desktopSettings),
      },
    },
    assert: {
      assertions: {
        'categories:performance': ['warn', { minScore: 0.85 }],
        'categories:accessibility': ['warn', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        // 350 KB gzipped JS budget (LHCI reports transfer size, which is gzipped over the wire).
        'resource-summary:script:size': ['warn', { maxNumericValue: 350 * 1024 }],
        'largest-contentful-paint': ['warn', { maxNumericValue: 2500 }],
        'total-blocking-time': ['warn', { maxNumericValue: 200 }],
      },
    },
    upload: {
      target: 'filesystem',
      // Resolved at runtime by capture_baseline.sh which sets LHCI_OUTPUT_DIR.
      outputDir: process.env.LHCI_OUTPUT_DIR || path.resolve(__dirname, 'reports', 'latest', 'lhci'),
      reportFilenamePattern: '%%PATHNAME%%-%%DATETIME%%-report.%%EXTENSION%%',
    },
  },
};
