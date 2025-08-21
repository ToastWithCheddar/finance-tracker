# Integration Map (living)

How to use:
- Link features to concrete files across layers.
- Keep it short; 1–3 bullets per feature.

Features
- Auth
  - BE: `backend/app/routes/auth.py` (prefix `/api/auth`)
  - FE: `frontend/src/services/userService.ts`, `frontend/src/pages/Login.tsx`

- Transactions
  - BE: `backend/app/routes/transactions.py` + include in `app.main` at `/api/transactions`
  - FE: `frontend/src/services/transactionService.ts`, `frontend/src/pages/Transactions.tsx`, `frontend/src/hooks/useTransactions.ts`
  - FE: `frontend/src/api/adapters/transaction.ts` (DTO → view model)

- Budgets
  - BE: `backend/app/routes/budget.py` at `/api/budgets`
  - FE: `frontend/src/services/budgetService.ts`, `frontend/src/pages/Budgets.tsx`, `frontend/src/hooks/useBudgets.ts`
  - FE: `frontend/src/api/adapters/budget.ts` (DTO → view model)

- Categories
  - BE: `backend/app/routes/categories.py` at `/api/categories`
  - FE: `frontend/src/services/categoryService.ts`, `frontend/src/pages/Categories.tsx`

- Notifications
  - BE: `backend/app/routes/notifications.py` at `/api/notifications`
  - FE: `frontend/src/services/notificationService.ts`, `frontend/src/hooks/useNotifications.ts`

- Accounts & Plaid
  - BE: `backend/app/routes/accounts_basic.py`, `accounts_plaid.py`, `accounts_sync.py`
  - FE: `frontend/src/services/accountService.ts`, `frontend/src/hooks/useAccounts.ts`, `frontend/src/components/plaid/*`

- ML Categorization
  - BE: `backend/app/routes/ml.py` at `/api/ml/*`
  - FE: `frontend/src/services/mlService.ts`, `frontend/src/hooks/useMerchantEnrichment.ts`

- Saved Filters
  - BE: `backend/app/routes/saved_filters.py`
  - FE: `frontend/src/services/savedFilterService.ts`, `frontend/src/hooks/useSavedFilters.ts`

Gaps to verify next:
- Ensure FE services align with prefixes in `backend/app/main.py` (notably `/api/...`).
- Replace ad-hoc service calls with generated client under `frontend/src/api/generated/`.
