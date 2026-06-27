# Security topology (post-W7)

How an authenticated request flows through the hardened backend, and where each
W7 control sits. Cited findings: BE-SEC-001..009, FE-SEC-001..004,
BE-CONC-001..002, BE-RL-001.

```mermaid
sequenceDiagram
    autonumber
    participant U as Browser
    participant N as nginx (443, HSTS)
    participant API as FastAPI (rate-limited)
    participant CSRF as CSRF middleware
    participant AUTH as Supabase JWT verify
    participant RLS as user_context_db()<br/>SET LOCAL app.user_id
    participant PG as Postgres (RLS policies)
    participant ENC as Encryption service<br/>(HKDF-SHA256)
    participant R as Redis<br/>(Lua CAS-DELETE)

    U->>N: TLS 1.2+ (HSTS, OCSP)
    N->>API: Forward + rate limit (SlowAPI)
    API->>CSRF: Verify cookie==header on mutating verbs
    CSRF->>AUTH: Read Bearer JWT
    AUTH-->>API: claims{sub, email}
    API->>RLS: Open async session in user_context_db
    RLS->>PG: Query (RLS filters by app.user_id)
    PG-->>API: Row set scoped to caller
    API->>ENC: encrypt(plaid_access_token)
    Note over ENC: Hard-fail on error<br/>(no plaintext fallback)
    API->>R: SET sync_lock:{acct} fence-token NX EX 60
    Note over R: Release uses Lua CAS:<br/>get == fence_token then DEL
    API-->>U: JSON response
```

```mermaid
flowchart TD
    subgraph "WebSocket auth (W7)"
        WS_A[Client opens WS<br/>unauthenticated]
        WS_B[Server expects<br/>first frame = auth]
        WS_C{token valid?}
        WS_D[Promote socket]
        WS_E[Close 4401<br/>Unauthorized]
    end
    WS_A --> WS_B --> WS_C
    WS_C -- yes --> WS_D
    WS_C -- no --> WS_E
```

## Mapping to findings

| Layer | Control | Finding(s) closed |
|---|---|---|
| nginx 443 + HSTS | TLS termination | INFRA-NGINX-002 |
| SlowAPI | per-route rate limits | BE-RL-001 |
| CSRF middleware | double-submit cookie + header | FE-SEC-001..003, BE-SEC-005 |
| Supabase JWT | `verify_supabase_token`, dev bypass gated | BE-SEC-002 |
| `user_context_db()` | async generator, SET LOCAL inside the with-block | BE-SEC-001 |
| `_provision_user_from_supabase` | INSERT … ON CONFLICT to fix TOCTOU | BE-CONC-001 |
| HKDF-SHA256 + typed `EncryptionError` | hard-fail; configurable hex salt | BE-SEC-003, BE-SEC-006 |
| Redis fence tokens (Lua CAS-DELETE) | sync-lock release safety | BE-CONC-002 |
| WS first-frame auth, close 4401 | WS handshake | BE-WS-001 (closed via FE-WS-001 fix), BE-SEC-008 |
| `.env.example` scrubbed | no live secrets | BE-SEC-004 |
| safetensors prototype I/O | no untrusted pickle | ML-SEC-001 |
