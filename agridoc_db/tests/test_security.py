"""Tests for agridoc_db.security primitives."""
import hashlib
import os
from agridoc_db.security import (
    compute_chain_hash,
    chain_head,
    hash_password,
    verify_password,
    compute_hmac,
    hmac_equals,
)


def _set_env_keys() -> None:
    os.environ["AGRIDOC_DB_KEYS"] = (
        "gE3yW1VqR4vH6kZ8mN0pQ2sT4uW6yA8cE0gI2kM4oQ="
        ","
        "aB4dF6hJ8lN0pR2tV4xZ6bD8fH0jL2nP4rT6vX8zB="
    )


def test_argon2_roundtrip() -> None:
    h = hash_password("secure-farmer-pass")
    assert h.startswith("$argon2id$")
    assert verify_password("secure-farmer-pass", h) is True
    assert verify_password("wrong-password", h) is False


def test_chain_hash_consistency() -> None:
    prev = chain_head()
    h1 = compute_chain_hash(prev, "login", '{"user":1}')
    h2 = compute_chain_hash(prev, "login", '{"user":1}')
    assert h1 == h2
    assert h1 != chain_head()


def test_chain_verification(starts_end_to_end) -> None:
    rows = list(starts_end_to_end)
    from agridoc_db.security import verify_chain
    assert verify_chain(rows) is True


def test_hmac_constant_time() -> None:
    os.environ["AGRIDOC_HMAC_SECRET"] = "my-secret-for-testing-purposes-only"
    mac = compute_hmac("test-data")
    assert hmac_equals(mac, mac)
    assert hmac_equals(mac, mac) is True


def test_hmac_differs_for_different_input() -> None:
    m1 = compute_hmac("data-a")
    m2 = compute_hmac("data-b")
    assert m1 != m2


# Fixture helper: build a valid chain and yield as list of dicts
import pytest


@pytest.fixture
def starts_end_to_end():
    from agridoc_db.security import compute_chain_hash, chain_head
    prev = chain_head()
    payload = '{"action":"login","user_id":"u1"}'
    h1 = compute_chain_hash(prev, "login", payload)
    prev = h1
    h2 = compute_chain_hash(prev, "diagnosis", '{"district":"x"}')
    return [
        {"prev_hash": chain_head(), "action": "login", "data_hash": h1, "payload_json": payload},
        {"prev_hash": h1, "action": "diagnosis", "data_hash": h2, "payload_json": '{"district":"x"}'},
    ]
