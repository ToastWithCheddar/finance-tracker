
# API Contract

*This is an inferred contract based on backend route analysis. It is not exhaustive.*

| METHOD | PATH | REQ BODY (fields) | RESP (fields) | Auth? | Notes |
| --- | --- | --- | --- | --- | --- |
| **Auth** | | | | | |
| `POST` | `/auth/login` | `username`, `password` | `access_token`, `refresh_token`, `token_type`, `expires_in` | No | Standard email/password login. |
| `POST` | `/auth/logout` | (none) | (none) | Yes | Logs out the current user. |
| `POST` | `/auth/refresh` | `refresh_token` | `access_token`, `refresh_token`, `token_type`, `expires_in` | No | Refreshes the access token. |
| `GET` | `/auth/me` | (none) | `id`, `email`, `full_name`, `is_active`, `is_superuser` | Yes | Fetches the current user's data. |
| **Accounts** | | | | | |
| `GET` | `/accounts/` | (none) | `List[Account]` | Yes | Get all accounts for the user. |
| `POST` | `/accounts/` | `AccountCreate` | `Account` | Yes | Create a new manual account. |
| `GET` | `/accounts/{account_id}` | (none) | `Account` | Yes | Get a specific account. |
| **Transactions**| | | | | |
| `GET` | `/transactions/` | `limit`, `offset`, `start_date`, etc. | `TransactionListResponse` | Yes | Get a paginated list of transactions. |
| `POST` | `/transactions/` | `TransactionCreate` | `TransactionResponse` | Yes | Create a new transaction. |
