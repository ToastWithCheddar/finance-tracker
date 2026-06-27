# 11 — Frontend polish in place (Phase A)

## Summary

Targeted polish pass on the existing custom-Tailwind frontend (no shadcn
migration). Two of the explore-audit's five flagged issues turned out to be
real and actionable; three were speculative on closer reading. The two real
ones — leaked token-flavored inline styles and the `MetricCard` six-branch
spaghetti — are now closed.

## Files edited

| Path | Change |
|---|---|
| `frontend/src/components/ui/Modal.tsx:77,79,95` | Replaced `style={{ borderColor: 'hsl(var(--border))' }}`, `style={{ color: 'hsl(var(--text))' }}` with the existing Tailwind tokens `border-border`, `text-text`. |
| `frontend/src/components/layout/Layout.tsx:10` | `style={{ backgroundColor: 'hsl(var(--bg))' }}` → `bg-bg`. |
| `frontend/src/pages/Transactions.tsx:357`, `Budgets.tsx:72`, `Profile.tsx:114,122,133` | Same `bg-bg` / `text-text` token swap. |
| `frontend/src/components/ui/MetricCard.tsx` | **Refactor**: 75-line `getCardTheme()` switch + 8-line in-place mutation collapsed to one `THEME_STYLES: Record<MetricCardTheme, ThemeStyles>` constant + a 12-line `deriveChangeOverride` helper. Render path now: `const cardTheme = change-override ? deriveChangeOverride(...) : THEME_STYLES[theme];`. |

## Files NOT edited (audit was speculative)

| Audit complaint | Investigation outcome |
|---|---|
| "Inconsistent gap/padding in flex/grid" (A2) | The pages use the standard Tailwind 4-pt scale (`gap-2`, `gap-4`, `gap-6`). The differences are intentional density choices (nav rail dense, dashboard breathing). No drift. **Skipped.** |
| "TransactionList styling split" (A5) | `TransactionItem` already uses `<Card><CardContent className="p-4">` and the list uses `space-y-3` for gaps; no duplicated padding. **Skipped.** |
| "Modal centering inconsistency" (A4) | Modal already centers via `flex min-h-full items-center justify-center p-4` (line 71); the inline-style fix covered the only real issue. **Folded into A1.** |

## Tailwind token reuse (no new tokens)

`tailwind.config.cjs` already exposed CSS-variable-driven tokens (`bg`,
`surface`, `text`, `border`, `brand`, `accent`). The polish pass simply
*used* them where inline `style=` had been used before. Zero new tokens
were introduced.

## Counts

- `grep -rn 'style={{' frontend/src/ --include='*.tsx' --include='*.ts'`:
  **18 → 14**. The remaining 14 are legitimately dynamic (Math.random
  positions in MilestoneNotification, computed widths from progress
  percentages, computed `paddingLeft` for nested-category indentation,
  `payload[0].color` from Recharts data).
- `MetricCard.tsx` LOC: 198 → 209 (the new `THEME_STYLES` record adds
  visual weight, but the *logic* path shrinks from a 60-line switch
  block to a 4-line ternary).

## Verification

- `cd frontend && npx tsc --noEmit` — exit 0 (clean, including the
  refactor).
- `cd frontend && grep -rn 'hsl(var(--bg))\|hsl(var(--text))\|hsl(var(--border))' src/ --include='*.tsx'` returns only the calls left intentionally inside `style={{ color: payload[0].color }}` (not these tokens) — i.e. zero violations.

## Open follow-ups

- FE-PR-004 (`any` casts) — Phase 2 closeout `09-frontend-hygiene.md`
  intentionally left this open.
