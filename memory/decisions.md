# Decisions (ADR-style)

Template
- Date: YYYY-MM-DD
- Context: Problem and options considered.
- Decision: Short statement of the chosen approach.
- Consequences: Tradeoffs and follow-ups (task IDs).

Entries
- Date: 2025-08-21
  - Context: Keep FE/BE in sync without over-engineering.
  - Decision: Contract-first; store backend OpenAPI under `memory/contracts/` and generate FE types/client.
  - Consequences: Add generation script; block merges if generated diff not clean.

