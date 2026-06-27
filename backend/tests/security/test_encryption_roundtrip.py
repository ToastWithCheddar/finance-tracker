"""BE-SEC-003 — Encryption fail-soft returns plaintext.

`backend/app/services/encryption_service.py:36-55` swallows every exception in
`encrypt()` and `decrypt()` and silently returns the input unmodified. That
means a Plaid access token that fails to encrypt is stored as plaintext in
the DB, and a corrupted ciphertext is "decrypted" to the still-encrypted
bytes. Both behaviours are catastrophic and silent.

This module pins the *desired* contract via Hypothesis property tests:

1. Round-trip: for any valid string `s`, `decrypt(encrypt(s)) == s`.
2. Hard-fail on decrypt error: feeding garbage into `decrypt()` MUST raise,
   not return the garbage. The test asserts that raising is the correct
   behaviour; today the service swallows and returns the garbage, so this
   test is xfail until the fix lands.

We import from the real backend module path
(`app.services.encryption_service`) rather than vendoring, per the audit
rule about not touching internship code.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings as hyp_settings, strategies as st

from app.services.encryption_service import EncryptionService


@pytest.fixture(scope="module")
def enc():
    # SECRET_KEY is set in conftest.py before app import, so this Fernet
    # initialisation uses the test key.
    return EncryptionService()


@pytest.mark.security
@hyp_settings(max_examples=50, deadline=None)
@given(st.text(min_size=0, max_size=1024))
def test_encrypt_decrypt_roundtrip_is_identity(enc, value: str):
    """For any UTF-8 string, decrypt(encrypt(x)) must equal x."""
    ct = enc.encrypt(value)
    assert ct is not None
    pt = enc.decrypt(ct)
    assert pt == value, (
        "BE-SEC-003 regression: round-trip lost data; "
        f"input={value!r} decrypted={pt!r}"
    )


@pytest.mark.security
def test_encrypt_none_returns_none(enc):
    assert enc.encrypt(None) is None
    assert enc.decrypt(None) is None


@pytest.mark.security
@pytest.mark.xfail(
    strict=False,
    reason="BE-SEC-003: decrypt() swallows InvalidToken and returns ciphertext",
)
@given(st.text(min_size=1, max_size=64).filter(lambda s: not s.startswith("gAAAA")))
@hyp_settings(max_examples=25, deadline=None)
def test_decrypt_raises_on_invalid_token(enc, garbage: str):
    """Garbage in must raise — never silently return the garbage."""
    with pytest.raises(Exception):
        enc.decrypt(garbage)


@pytest.mark.security
@pytest.mark.xfail(
    strict=False,
    reason="BE-SEC-003: encrypt() catches Exception and returns plaintext",
)
def test_encrypt_does_not_silently_return_plaintext(enc, monkeypatch):
    """If the underlying Fernet call raises, encrypt() MUST propagate, not
    return the plaintext (which would then be stored in the DB as if it were
    a ciphertext — the actual production bug)."""

    class _Boom:
        def encrypt(self, *_a, **_kw):
            raise RuntimeError("simulated cipher failure")

    monkeypatch.setattr(enc, "_fernet", _Boom())

    plaintext = "plaid-access-token-abcdef"
    with pytest.raises(Exception):
        result = enc.encrypt(plaintext)
        # If we reach here, the function returned something — make sure it
        # at least is NOT the plaintext (which is the documented bug).
        assert result != plaintext, (
            "BE-SEC-003 regression: encrypt() returned plaintext on error"
        )
