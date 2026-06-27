# Frontend Performance Benchmarking

Self-contained Lighthouse CI + bundle analyzer + Playwright trace scaffolding for the finance-tracker frontend. Captures a baseline against whatever `frontend/vite.config.ts` is currently configured for — so it benchmarks production builds regardless of whether minification has been flipped on yet.

This directory is the **only** place to install dependencies for these tools. Do **not** install anything at the repo root or in `frontend/`.

## Prerequisites

- Node.js 20+
- A built `frontend/dist/` directory. The baseline script will fail loudly if it is missing.
- Chrome / Chromium installed locally (Lighthouse). Playwright installs its own browser via `npx playwright install chromium` (run once after `npm install`).

## Install

```bash
cd benchmarks/frontend
npm install
npx playwright install chromium   # one-time, ~150 MB
```

## Build the frontend first

The harness intentionally does not modify `frontend/`. Build it via the existing scripts:

```bash
cd ../../frontend
npm ci          # only if node_modules is missing
npm run build   # produces frontend/dist/
```

## Run the full baseline

```bash
cd benchmarks/frontend
npm run baseline
```

Outputs land in `reports/<git-sha>/`:

- `lhci/` — Lighthouse CI HTML + JSON reports (3 runs, median used)
- `bundle-summary.json` — per-chunk raw + gzip sizes, grouped by route hint
- `dashboard-trace.json` — LCP / FCP / TBT plus a Playwright performance trace
- `meta.json` — timestamp, node version, git SHA, form factor

## Individual targets

| Command | What it does |
|---|---|
| `npm run lhci` | Just Lighthouse CI (`lhci autorun`) against `npm run preview` |
| `npm run analyze:bundle` | Just gzip-size analysis of `frontend/dist/assets/*.js` |
| `npm run trace:dashboard` | Just the Playwright dashboard trace |
| `npm run type-check` | `tsc --noEmit` on the harness sources |

## Mobile vs desktop

LHCI defaults to **desktop**. To run mobile:

```bash
LHCI_FORM_FACTOR=mobile npm run lhci
```

## Budgets

Configured in `lighthouserc.cjs`:

- Performance score >= 0.85
- Accessibility score >= 0.90
- Best-Practices score >= 0.90
- Total JS transfer <= 350 KB gzipped
- LCP <= 2500 ms
- TBT <= 200 ms

Budgets are advisory in this foundation wave — failures surface in the report but do not gate CI yet.

## Notes

- The bundle analyzer is **dependency-free at runtime**: it reads `frontend/dist/assets/*.js`, gzips them in memory via Node's `zlib`, and groups by filename hash prefix. It works whether Vite emits a `manifest.json`, sourcemaps, or neither.
- `rollup-plugin-visualizer` is pinned in `devDependencies` so an operator can opt-in via a one-off Vite plugin invocation if a richer treemap is needed; it is not wired into `frontend/vite.config.ts` (modularity rule).
- All paths in scripts are computed relative to this directory using `import.meta.url`, so `npm run baseline` works regardless of the caller's CWD.
