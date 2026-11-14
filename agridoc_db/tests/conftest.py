"""Fixtures and conftest for agridoc_db tests."""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Must set DATABASE_URL BEFORE importing models/engine
def _setup_test_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="agridoc_test_")
    os.close(fd)
    os.environ["AGRIDOC_DATABASE_URL"] = f"sqlite:///{path}"
    os.environ["AGRIDOC_DB_KEYS"] = (
        "gE3yW1VqR4vH6kZ8mN0pQ2sT4uW6yA8cE0gI2kM4oQ="
        ","
        "aB4dF6hJ8lN0pR2tV4xZ6bD8fH0jL2nP4rT6vX8zB="
    )
    os.environ["AGRIDOC_HMAC_SECRET"] = "test-hmac-secret-for-unittests"
    os.environ["AGRIDOC_DB_VALIDATE"] = "1"

_setup_test_db()

from agridoc_db.models import Base
from agridoc_db.engine import get_engine, reset_engine


@pytest.fixture(scope="session", autouse=True)
def _reset_engine_for_tests():
    """Reset engine to pick up test DATABASE_URL."""
    reset_engine()
    yield
    reset_engine()


@pytest.fixture(scope="session")
def tmp_db() -> Generator[str, None, None]:
    """Return the test database URL (already set up in module init)."""
    yield os.environ["AGRIDOC_DATABASE_URL"]


@pytest.fixture()
def session(tmp_db: str) -> Generator[Session, None, None]:
    """Provide an in-session-scoped ORM session with tables created and rolled back."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    conn = engine.connect()
    trans = conn.begin()
    sess = Session(bind=conn)
    yield sess
    sess.close()
    trans.rollback()
    conn.close()
