"""AgriDoc AI database package.

SQLAlchemy 2.x models for the AgriDoc AI platform. 15 tables:

  users, sessions, diagnoses, feedback, expert_reviews, hotspots,
  outbreak_aggregates, market_prices, weather_cache, advisory_kb,
  translations, sync_queue, audit_log, key_registry, model_versions

Privacy architecture:
  * No raw images, no emails, no phone numbers, no device IDs are stored.
  * Diagnoses are anonymous by default; a farmer opts in to persistence.
  * Every sensitive operation writes an immutable, hash-chained audit row.
  * Row-level security (PostgreSQL) isolates sessions between users.
"""
from __future__ import annotations

from .engine import DATABASE_URL, get_session, health_check, engine, SessionLocal

__all__ = [
    "DATABASE_URL",
    "get_session",
    "health_check",
    "engine",
    "SessionLocal",
    "Base",
    "UTCDateTime",
    "User",
    "Session",
    "Diagnosis",
    "Feedback",
    "ExpertReview",
    "Hotspot",
    "OutbreakAggregate",
    "MarketPrice",
    "WeatherCache",
    "AdvisoryKB",
    "Translation",
    "SyncQueue",
    "AuditLog",
    "KeyRegistry",
    "ModelVersion",
    "TrainingLog",
    "Recommendation",
    "get_fernet",
    "encrypt",
    "decrypt",
    "hash_password",
    "verify_password",
    "compute_hmac",
    "hmac_equals",
    "compute_chain_hash",
    "chain_head",
    "verify_chain",
    "record_diagnosis",
    "get_advice",
    "record_feedback",
    "record_hotspot",
    "k_anonymity_outbreak_report",
    "delete_my_data",
    "rotate_key",
    "purge_expired",
    "export_retraining_data",
    "get_pending_sync",
    "mark_synced",
    "add_sync_entry",
]