"""SQLAlchemy 2.x models for AgriDoc AI platform.

15 tables with privacy-first design:
  - No raw images, no emails, no phone numbers, no device IDs stored.
  - Diagnoses are anonymous by default; farmer opts in via `consent`.
  - Sensitive PII (tts_phone) is encrypted with Fernet/MultiFernet.
  - Every sensitive operation writes an immutable, hash-chained audit row.
  - Row-level security (PostgreSQL) isolates sessions between users.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """UTC DateTime type with timezone awareness.

    Stores timestamps as UTC-aware in PostgreSQL and UTC-string in SQLite
    (which has no native timezone type). All reads return tz-aware datetimes.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    """Base class with automated ``created_at`` / ``updated_at``."""

    pass


# Helper
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Models
class User(Base):
    """Farmer account (optional — diagnoses can be anonymous)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    email_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    phone_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    session_expiry: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """User session with expiry. Isolated per-user via RLS in PG."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, index=True
    )

    user = relationship("User", back_populates="sessions")
    diagnoses = relationship("Diagnosis", back_populates="session")


class Diagnosis(Base):
    """Leaf-image diagnosis. Contains client-generated idempotency key."""

    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True
    )
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    crop: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    predicted_class: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_k_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consent_persist: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_voice: Mapped[bool] = mapped_column(Boolean, default=False)
    # client-generated idempotency key for replay protection
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    session = relationship("Session", back_populates="diagnoses")
    feedbacks = relationship("Feedback", back_populates="diagnosis", cascade="all, delete-orphan")
    hotspots = relationship("Hotspot", back_populates="diagnosis", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_diagnoses_district_created", "district", "created_at"),
    )


class Feedback(Base):
    """Farmer-corrected label (ground truth for retraining)."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=True
    )
    class_label: Mapped[str] = mapped_column(String(200), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # replay guard: same as diagnosis idempotency_key when supplied
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    diagnosis = relationship("Diagnosis", back_populates="feedbacks")

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_feedback_idem"),
    )


class ExpertReview(Base):
    """Expert-reviewed diagnosis (confirmed = gold label)."""

    __tablename__ = "expert_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False
    )
    expert_id: Mapped[uuid.UUID] = mapped_column(PG_UUID, nullable=False)
    confirmed_class: Mapped[str] = mapped_column(String(200), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


class Hotspot(Base):
    """Per-diagnosis hotspot entry (feeds outbreak_aggregates)."""

    __tablename__ = "hotspots"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=True
    )
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    crop: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disease: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    diagnosis = relationship("Diagnosis", back_populates="hotspots")


class OutbreakAggregate(Base):
    """Materialized-ish aggregate for fast district dashboards. Refreshed by job."""

    __tablename__ = "outbreak_aggregates"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    disease: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    week_start: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    refreshed_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        UniqueConstraint("district", "disease", "week_start", name="uq_ob_district_disease_week"),
        Index("ix_ob_district_week", "district", "week_start"),
    )


class MarketPrice(Base):
    """Ingested market price record (Agmarknet / e-NAM)."""

    __tablename__ = "market_prices"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    commodity: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    min_price: Mapped[float] = mapped_column(Float, nullable=True)
    max_price: Mapped[float] = mapped_column(Float, nullable=True)
    modal_price: Mapped[float] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        Index("ix_market_commodity_fetched", "commodity", "fetched_at"),
    )


class WeatherCache(Base):
    """Cached weather record with expiry and staleness flag."""

    __tablename__ = "weather_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disease_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_weather_district_fetched", "district", "fetched_at"),
    )


class AdvisoryKB(Base):
    """Treatment knowledge base entries (non-LLM advice)."""

    __tablename__ = "advisory_kb"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    class_label: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        Index("ix_advisory_class_lang", "class_label", "language"),
    )


class Translation(Base):
    """UI string translations for 10 languages."""

    __tablename__ = "translations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        UniqueConstraint("key", "language", name="uq_translation_key_lang"),
    )


class SyncQueue(Base):
    """Offline queue for diagnoses sent from mobile without connectivity."""

    __tablename__ = "sync_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    ts: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    image_b64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    predicted_class: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    farmer_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    farmer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synced: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_sync_ts_synced", "ts", "synced"),
    )


class AuditLog(Base):
    """Immutable, hash-chained audit log. Cannot be modified after insertion."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(200), nullable=True)
    target_table: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_ts_action", "ts", "action"),
        Index("ix_audit_action_target", "action", "target_id"),
        Index("ix_audit_prev_data", "prev_hash", "data_hash"),
    )


class KeyRegistry(Base):
    """Keeps multiple Fernet keys for MultiFernet rotation support."""

    __tablename__ = "key_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    fernet_key_b64: Mapped[str] = mapped_column(String(44), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        Index("ix_key_registry_index", "key_index"),
    )


class ModelVersion(Base):
    """Tracks model versions used for diagnoses (drift detection)."""

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    backbone: Mapped[str] = mapped_column(String(100), nullable=False)
    checkpoint_path: Mapped[str] = mapped_column(String(500), nullable=True)
    top1_acc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top3_acc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macro_f1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


class TrainingLog(Base):
    """Legacy table preserved from earlier build (kept for backward compat)."""

    __tablename__ = "training_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow, nullable=False)
    backbone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    epochs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top1_acc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top3_acc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macro_f1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checkpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Recommendation(Base):
    """Market/weather advisory generated for a district/crop combo."""

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID, primary_key=True, default=uuid.uuid4
    )
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    crop: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rec_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # "sell_now", "hold", "irrigate", "spray_organic"
    priority: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_price_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID, ForeignKey("market_prices.id", ondelete="SET NULL"), nullable=True
    )
    source_weather_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID, ForeignKey("weather_cache.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
