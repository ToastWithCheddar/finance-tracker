# Runbooks

Operational playbooks for production-relevant procedures.

| Runbook | Purpose |
|---|---|
| `backup.md` | Postgres backup, restore, and disaster-recovery procedure. |
| `tls-options.md` | TLS termination options (nginx, Caddy, managed LB) and cert rotation. |
| `model-fetch.md` | How the ML model artifact is fetched, pinned, and verified at deploy time. |
| `csrf-strategy.md` | CSRF defense strategy across the cookie-auth flow. |
| `encryption-migration.md` | At-rest encryption rollout and key-rotation playbook. |
| `security-checklist.md` | Pre-release security checklist. |
| `observability-stack.md` | Logging / metrics / tracing stack deployment and operation. |
