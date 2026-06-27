# Encryption key rotation / migration runbook

Closes BE-SEC-003.

## Background

The pre-W7 encryption service silently fell back to **plaintext** on any
encrypt/decrypt error. As a result, some Plaid access tokens may be on disk
in the clear, alongside legitimately-encrypted Fernet ciphertexts.

The new service:

- Derives Fernet keys via **HKDF-SHA256** over `SECRET_KEY` with a
  configurable salt `ENCRYPTION_KEY_SALT` (32 random bytes, hex).
- Raises a typed `EncryptionError` on failure — no silent plaintext.

## One-time pre-deploy steps

1. **Generate the salt** if not already set:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Store as `ENCRYPTION_KEY_SALT` in the environment / secret manager.

2. **Diagnostic scan** of existing rows. Read-only, no mutations:

   ```bash
   python -m app.services.encryption_migration
   ```

   Expected output per encrypted column:

   ```
   [accounts.plaid_access_token] total=N null=… decryptable=… undecryptable=… suspected_plaintext=…
   ```

3. **Triage**:

   - `decryptable` = healthy, leave alone.
   - `suspected_plaintext` = the BE-SEC-003 fallout. **Re-encrypt**: fetch
     the value, encrypt it via the new service, write it back. This is a
     one-shot SQL migration (Alembic data migration recommended).
   - `undecryptable` = either truly corrupt or encrypted with a different
     key. Cannot be salvaged without the old key — coordinate with the
     account owner to refresh the upstream credential (e.g. relink Plaid).

## Key rotation (future)

Rotation is intentionally out of scope for this fix — we did **not** add an
auto-rotate path. The procedure for the future:

1. Stand up the new key alongside the old (`SECRET_KEY` + `ENCRYPTION_KEY_SALT_OLD`).
2. Decrypt with old, encrypt with new, write back. Wrap in a transaction.
3. Flip `ENCRYPTION_KEY_SALT` to the new value, redeploy.
4. Retain `_OLD` for one release window in case of rollback.

## Verification checklist

- [ ] `ENCRYPTION_KEY_SALT` set in production / staging.
- [ ] `python -m app.services.encryption_migration` reports zero
      `suspected_plaintext` and zero `undecryptable` after migration.
- [ ] App boots without "ephemeral salt" warnings.
