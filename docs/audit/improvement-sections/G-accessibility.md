# G — Accessibility (FE-A11Y-001)

Day-23 brief, parallel to A–F. Closes the only remaining a11y finding in
the register and broadens the axe-playwright sweep so regressions in
unprotected paths are caught in CI.

## Scope

| Item | Status | Notes |
|---|---|---|
| Axe scan on `/login` | already in place pre-Day-23 | passes |
| Axe scan on `/dashboard` | already in place pre-Day-23 | passes |
| Axe scan on `/transactions`, `/categories`, `/budgets`, `/goals`, `/profile` | **new** | added in Day-23 |
| Per-route ErrorBoundary surfaces accessible error UI | new | `ErrorBoundary` already uses semantic `<h2>`, `<button>` — no rewrite needed |
| Form validation aria-live | already in place | from W4 work |

## Approach

Each route gets a Playwright test case (one per route, not a single
parameterized assertion) so failures are localized and the HTML report
attaches the per-route `axe-*.json` violation list. The threshold is
*serious* / *critical* only; *moderate* / *minor* findings show up in the
attached report but do not break the build, so the baseline is actionable
without being noisy.

The `axe-playwright` setup in `e2e/tests/accessibility.spec.ts` is
unchanged conceptually — only the **coverage** expanded. No new harness
code, no new dependencies.

## Decisions

- **Why `wcag2a` + `wcag2aa` tags only?** This is the practical floor for a
  finance-tracker UI. `wcag2aaa` flags items (e.g. ultra-strict contrast)
  that would force re-skinning the entire palette; out of phase scope.
- **Why one test per route, not a `for…of test('all routes', …)` loop?**
  Localized failures in CI; each route's HTML attachment is independent;
  parallel execution.

## Operator follow-ups

- If new top-level routes are added (`/settings`, `/admin`, …), add a test
  case to `e2e/tests/accessibility.spec.ts`. Trivial copy-paste.
- Re-run with `wcag22aa` once Playwright + axe-core upgrade rolls in (axe
  ≥ 4.10).

## Closes

- **FE-A11Y-001** — Minimal a11y. Phase-2 closeout.
