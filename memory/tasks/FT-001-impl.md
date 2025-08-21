# TaskSpec: FT-001 Implementation — Transactions List Refactor

- ID: FT-001
- Purpose: Refactor the Transactions list fetch to use contract-aligned params and adapter-based mapping with the generated types.

## Context
- Backend list endpoint: GET `/api/transactions` with query params:
  - `start_date`, `end_date`, `account_id`, `category_id`, `status`,
  - `min_amount_cents`, `max_amount_cents`, `search_query`,
  - `is_recurring`, `is_transfer`, `group_by`, `limit`, `offset`.
- Backend returns a list envelope like: `{ transactions, total, limit, offset, has_more }`.
  - `normalizeListEnvelope` already adapts to this and computes `{ page, per_page, pages }`.
- Generated types are available under `frontend/src/api/generated/types.ts`.
- Goal: keep minimal surface changes — use the adapter for items and keep the current frontend list shape (with `pages`).

## Files To Touch
- `frontend/src/services/transactionService.ts` (edit method `getTransactions`)
- `frontend/src/api/adapters/transaction.ts` (ensure export `toTransactionView`; keep `toTransactionList` as optional utility)
- `memory/integration-map.md` (add the adapter path under Transactions)

## Exact Changes
1) In `frontend/src/services/transactionService.ts`:
   - Import the adapter:
     - Add: `import { toTransactionView } from '../api/adapters/transaction';`
   - Fix request param mapping to align with backend:
     - Replace `min_amount` with `min_amount_cents`.
     - Replace `max_amount` with `max_amount_cents`.
     - Use `search_query` for `filters.search`.
     - If `filters.group_by` is set, send `group_by`.
     - Keep pagination behavior: compute `limit` and `offset` from `page` and `per_page`.
   - Replace inline item normalization with adapter:
     - Keep using `normalizeListEnvelope(response)` to compute `{ items, total, page, per_page, pages }`.
     - Map items: `const items = list.items.map(toTransactionView)`.
     - Return the same structure the method currently returns (including `pages`).
   - Do not touch other methods (create/update/delete/export) in this task.

2) In `frontend/src/api/adapters/transaction.ts`:
   - Ensure the adapter exports:
     - `export function toTransactionView(dto: any): Transaction { ... }`
   - Map snake_case → FE view model fields and also preserve raw backend fields to avoid breaking other code during migration:
     - Examples: `account_id → accountId`, `category_id → categoryId`, `amount_cents → amountCents`, `transaction_date → transactionDate`, `is_recurring → isRecurring`.
     - Default `currency` to `'USD'` if missing and coerce date to `YYYY-MM-DD` strings.
   - Leave `toTransactionList` helper as-is (optional utility, not used yet).

3) In `memory/integration-map.md`:
   - Under Transactions, add:
     - FE: `frontend/src/api/adapters/transaction.ts` (DTO → view model)

## Acceptance Criteria
- Calls to GET `/api/transactions` use contract-aligned params:
  - `min_amount_cents`, `max_amount_cents`, `search_query`, optional `group_by`, `limit`, `offset`.
- `getTransactions` returns the same list structure used by the UI/tests:
  - `{ items, total, page, per_page, pages }` with items adapted via `toTransactionView`.
- `npm --prefix frontend run type-check` passes.
- `./scripts/smoke.sh` succeeds (backend health + frontend build).
- No UI behavior regressions on Transactions page.

## Pitfalls
- Backend filter names differ from legacy FE:
  - Use `min_amount_cents` and `max_amount_cents` (not `min_amount`/`max_amount`).
  - Use `search_query` (not `search` or `merchant`).
- Date fields must remain strings (`YYYY-MM-DD`) in the view model.
- Do not change the shape of the returned list object (keep `pages`).

## Steps (Claude)
1) Update `transactionService.ts` param mapping and list mapping per above.
2) Import and use `toTransactionView` for item mapping; keep `normalizeListEnvelope` for pagination calculations.
3) Update `memory/integration-map.md` to add the adapter reference under Transactions.

## Local Test Commands
- Type-check: `npm --prefix frontend run type-check`.
- Smoke: `./scripts/smoke.sh`.
- Optional page tests: `npm --prefix frontend run test -- Transactions`.

