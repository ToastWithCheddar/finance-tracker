# Project Documentation

This document serves as the central hub for all documentation related to the Personal Finance Management Application. Its purpose is to provide a comprehensive guide for developers, maintainers, and future contributors.

## Table of Contents

1.  **[Architecture & Design Overview](./docs/architecture.md)**
    *   High-level diagrams for system, Docker, ML, and real-time flows.
    *   Clear explanations of how each subsystem interacts.
    *   Rationale for major technology choices.

2.  **[Frontend Component Breakdown](./docs/frontend.md)**
    *   Each React component’s role, props/state shape, data flow, and interaction points.

3.  **[Backend API & Services](./docs/backend.md)**
    *   Each FastAPI endpoint, its purpose, request/response schema, and associated database models.

4.  **[Machine Learning Pipeline](./docs/machine-learning.md)**
    *   Pipeline stages, models used, inference details, and performance benchmarks.

5.  **[Real-time Systems](./docs/real-time-systems.md)**
    *   WebSocket architecture, message types, and event handling.

6.  **[Data & Schema](./docs/data-and-schema.md)**
    *   Entity Relationship Diagram (ERD) for PostgreSQL schema.
    *   Field definitions, constraints, indexes, and relationships.
    *   Redis usage patterns.

7.  **[API & Real-time Event Reference](./docs/api-reference.md)**
    *   REST endpoints: method, path, parameters, request/response examples.
    *   WebSocket message types, payload formats, and triggering conditions.

8.  **[Operational Notes](./docs/operational-notes.md)**
    *   Local development setup and run instructions.
    *   Deployment process, including Docker Compose workflows.
    *   Testing approach and coverage summary.

9.  **[Cross-Cutting Concerns](./docs/cross-cutting-concerns.md)**
    *   Security (auth flows, sensitive data handling).
    *   Performance tuning techniques.
    *   Error handling patterns.

10. **[Glossary & Domain Knowledge](./docs/glossary.md)**
    *   Definitions of financial terms, ML jargon, and internal abbreviations.

11. **[Knowledge Capture & Decision History](./docs/decision-log.md)**
    *   Key design decisions and trade-offs.
    *   Known limitations and planned improvements.
