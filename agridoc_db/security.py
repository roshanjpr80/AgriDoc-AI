"""Security primitives for AgriDoc AI database.

- Password hashing: argon2id (via argon2-cffi)
- Encryption: MultiFernet with key rotation support
- HMAC lookup: constant-time equality checks for idempotency keys
- Audit chain: hash-chained immutable log entries
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

log = logging.getLogger("agridoc_db.security")

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a password with argon2id. Returns the full hash string."""
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its argon2id hash. Constant-time."""
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# MultiFernet encryption with key rotation
def _load_fernet_keys() -> list[bytes]:
    """Load Fernet keys from env var AGRIDOC_DB_KEYS (comma-separated b64).

    Falls back to AGRIDOC_DB_KEY if only one key is present.
    Raises ValueError if no keys are configured.
    """
    raw = os.environ.get("AGRIDOC_DB_KEYS", "") or os.environ.get("AGRIDOC_DB_KEY", "")
    if not raw.strip():
        raise ValueError(
            "AGRIDOC_DB_KEYS (or AGRIDOC_DB_KEY) not set. "
            "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    keys = [k.strip().encode() for k in raw.split(",") if k.strip()]
    if not keys:
        raise ValueError("No valid Fernet keys found in AGRIDOC_DB_KEYS")
    return keys


def get_fernet() -> MultiFernet:
    """Return a MultiFernet instance for encrypt/decrypt with rotation."""
    keys = _load_fernet_keys()
    return MultiFernet([Fernet(k) for k in keys])


def encrypt(plaintext: str) -> bytes:
    """Encrypt with the primary (latest) Fernet key."""
    fernet = get_fernet()
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes) -> str:
    """Decrypt trying all registered keys in order (MultiFernet)."""
    fernet = get_fernet()
    try:
        return fernet.decrypt(ciphertext).decode("utf-8")
    except InvalidToken:
        log.warning("Decryption failed - possible key rotation mismatch")
        raise


# HMAC helpers
def _hmac_secret() -> bytes:
    raw = os.environ.get(
        "AGRIDOC_HMAC_SECRET",
        hashlib.sha256(os.environ.get("AGRIDOC_API_KEYS", "dev-key").encode()).digest(),
    )
    return raw[:32].encode() if isinstance(raw, str) else raw[:32]


def compute_hmac(data: str) -> str:
    """Compute HMAC-SHA256 of data. Used for idempotency validation."""
    return hmac.new(_hmac_secret(), data.encode("utf-8"), hashlib.sha256).hexdigest()


def hmac_equals(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    return hmac.compare_digest(a.encode(), b.encode())


# Hash-chained audit log
def compute_chain_hash(prev_hash: str, action: str, payload: str) -> str:
    """SHA-256(prev_hash || ':' || action || ':' || payload)."""
    raw = f"{prev_hash}:{action}:{payload}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def chain_head() -> str:
    """Genesis block hash - SHA-256 of empty string."""
    return hashlib.sha256(b"").hexdigest()


def verify_chain(rows: list[dict]) -> bool:
    """Verify the audit chain integrity across a list of audit rows.

    Each row must have 'prev_hash', 'action', and 'data_hash' keys.
    """
    expected_prev = chain_head()
    for row in rows:
        action = row.get("action", "")
        payload = row.get("payload_json", "") or ""
        expected_hash = compute_chain_hash(expected_prev, action, payload)
        actual_hash = row.get("data_hash", "")
        if not hmac_equals(expected_hash, actual_hash):
            return False
        expected_prev = actual_hash
    return True
