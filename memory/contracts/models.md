# Shared Models (draft)

- Money
  - fields: amount (number), currency (string, ISO 4217)

- Pagination
  - fields: page (int), per_page (int), total (int)

- Transaction
  - id (string), account_id (string), amount (Money), date (string, date),
    description (string), merchant (string?), category (string?), notes (string?)

- Budget
  - id (string), name (string), period (enum: monthly|weekly|yearly),
    limit (Money), spent (Money), category (string?)
