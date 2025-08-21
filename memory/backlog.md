# Backlog (Single Queue)

Format: FT-### | Title | Short description | Status

- FT-001 | FE client/types from OpenAPI | Generate TS types and client from backend OpenAPI and wire for one page | Done
- FT-002 | Adapter layer for transactions | Map backend Transaction DTO → FE view model; refactor Transactions service to use adapter | Done
- FT-003 | Grouped transactions support | Add grouped fetch method returning adapted groups | Done
- FT-004 | Wire Transactions UI to grouping | Add UI control/toggle for group_by and use grouped method in one view | Done
- FT-005 | Contract params sweep | Replace ad‑hoc params with contract names across services (low-risk sweep) | Todo
- FT-006 | Expand smoke checks | Add a couple contract-based GETs and FE preview ping to smoke script | Done
- FT-007 | Fix TS issue in utils/account | Resolve pre-existing TypeScript config error blocking full smoke build | Todo
- FT-008 | Next adapter (budgets) | Generate types and add budgets adapter; refactor one usage | Todo
 
Status updates:
- FT-005 | Contract params sweep | Replace ad‑hoc params with contract names across services (low-risk sweep) | Done
- FT-007 | Fix TS issue in utils/account | Resolve pre-existing TypeScript config error blocking full smoke build | Done

New tasks:
- FT-008 | Budgets adapter + service | Add budgets adapter and align FE service to contract; refactor one view | Todo
- FT-009 | Saved filters alignment | Align saved filter service with contract; verify list/create/update/delete | Todo
- FT-010 | Merchants alignment | Align recognition/enrich/correct/suggestions endpoints + adapter | Todo
