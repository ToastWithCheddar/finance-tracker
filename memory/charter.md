# Finance Tracker — Project Charter

Purpose: Deliver a development-friendly, end-to-end personal finance tracker with simple, working integrations across backend, frontend, and ML.

Goals:
- Minimal working features; prioritize complete functionality over polish.
- Contract-first integration between backend and frontend.
- Lightweight automation via scripts; simple docs in Markdown.

Non-goals:
- Production-grade infra, hardening, or complex pipelines.
- Heavy test coverage mandates; prefer smoke checks and nearby tests only.

Principles:
- Small, focused changes (≤3 files when possible).
- Generated types from OpenAPI for FE; adapters map DTOs → view models.
- Keep shared memory accurate and concise.

