"""Database engine and session factory.

Supports SQLite (dev/test) and PostgreSQL (prod) via the
AGRIDOC_DATABASE_URL environment variable. Connection pooling is configured
here so every consumer shares one pool.

Engine is created lazily on first access to allow tests to set DATABASE_URL.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger("agridoc_db.engine")

_engine: Optional[Engine] = None
_sessionmaker: Optional[sessionmaker] = None


def _get_database_url() -> str:
    return os.environ.get("AGRIDOC_DATABASE_URL", "sqlite:///./data/agridoc.db")


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql")


def _create_engine() -> Engine:
    """Create the SQLAlchemy engine with proper configuration."""
    url = _get_database_url()
    is_sqlite = _is_sqlite(url)
    is_postgres = _is_postgres(url)

    pool_kwargs: dict = {}
    if is_postgres:
        pool_kwargs = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }

    eng = create_engine(url, future=True, echo=False, **pool_kwargs)

    if is_sqlite:
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_conn, _conn_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


def get_engine() -> Engine:
    """Get or create the singleton engine."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_sessionmaker() -> sessionmaker:
    """Get or create the sessionmaker bound to the engine."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _sessionmaker


# Backward compatibility: module-level attributes that lazily initialize
class _LazyEngine:
    def __getattr__(self, name):
        return getattr(get_engine(), name)


class _LazySessionMaker:
    def __getattr__(self, name):
        return getattr(get_sessionmaker(), name)


engine = _LazyEngine()
SessionLocal = _LazySessionMaker()


def get_session() -> Session:
    """FastAPI-style dependency: yield a session, close it after the request."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def health_check() -> dict:
    """Run a trivial query and return latency + backend info."""
    t0 = time.perf_counter()
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - t0) * 1000
        url = _get_database_url()
        return {
            "ok": True,
            "backend": "sqlite" if _is_sqlite(url) else "postgresql",
            "latency_ms": round(latency_ms, 2),
            "url": url.split("@")[-1] if "@" in url else url,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def reset_engine() -> None:
    """Reset the engine (mainly for testing)."""
    global _engine, _sessionmaker
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _sessionmaker = None


# Backward compatibility
def get_database_url() -> str:
    return _get_database_url()


# For `from .engine import DATABASE_URL` compatibility
DATABASE_URL = _get_database_url()