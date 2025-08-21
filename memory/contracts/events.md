# Domain Events (draft)

- TransactionCategorized
  - when: transaction category set/updated
  - payload: { transaction_id, user_id, old_category?, new_category, source: manual|ml|rule, timestamp }

- BudgetThresholdCrossed
  - when: budget spending crosses alert threshold
  - payload: { budget_id, user_id, period, spent, threshold, timestamp }

- AccountSyncCompleted
  - when: background sync finishes
  - payload: { account_id, user_id, totals, changes_count, started_at, finished_at }
