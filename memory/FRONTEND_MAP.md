
# Frontend Map

| ROUTE | COMPONENT(S) | DATA NEEDED | CURRENT CALL | SHOULD CALL (from API_CONTRACT) | MAPPING/ADAPTER NEEDED |
| --- | --- | --- | --- | --- | --- |
| `/` (root) | `App.tsx` | User auth state | (none) | `GET /auth/me` | Yes, create `authService`. |
| `/login` | `LoginPage` (to be created) | (none) | (none) | `POST /auth/login` | Yes, create `authService`. |
| `/accounts` | `AccountsList.tsx` (TBD), `AccountListItem.tsx` | List of accounts | Mock data | `GET /accounts/` | Yes, create `accountService`. |
| `/transactions`| `TransactionList.tsx` (TBD) | List of transactions | `transactionService.getTransactions` (exists) | `GET /transactions/` | `transactionService` already provides this. May need minor tweaks. |
