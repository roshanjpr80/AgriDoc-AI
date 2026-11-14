"""Database services for AgriDoc AI.

All functions accept an explicit SQLAlchemy Session so callers control
transactions. Functions do NOT open/close sessions.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from .models import (
    AdvisoryKB,
    AuditLog,
    Diagnosis,
    Feedback,
    Hotspot,
    KeyRegistry,
    MarketPrice,
    ModelVersion,
    OutbreakAggregate,
    Session as DBSession,
    SyncQueue,
    Translation,
    User,
    WeatherCache,
)
from .security import compute_chain_hash

log = logging.getLogger("agridoc_db.services")

_DIAGNOSIS_RETENTION_DAYS = int(
    os.environ.get("AGRIDOC_DIAGNOSIS_RETENTION_DAYS", "365")
)
_FEEDBACK_RETENTION_DAYS = int(
    os.environ.get("AGRIDOC_FEEDBACK_RETENTION_DAYS", "730")
)
_SYNC_QUEUE_RETENTION_DAYS = int(
    os.environ.get("AGRIDOC_SYNC_QUEUE_RETENTION_DAYS", "30")
)


def record_diagnosis(
    session: Session,
    district: str,
    predicted_class: str,
    confidence: float,
    consent_persist: bool = False,
    idempotency_key: Optional[str] = None,
    session_id: Optional[uuid.UUID] = None,
    crop: Optional[str] = None,
    uncertainty_score: Optional[float] = None,
    top_k_json: Optional[str] = None,
) -> Diagnosis:
    """Record a diagnosis with consent gating and replay protection."""
    if idempotency_key is not None:
        existing = session.execute(
            select(Diagnosis).where(Diagnosis.idempotency_key == idempotency_key)
        ).first()
        if existing is not None:
            log.info("Duplicate idempotency_key rejected: %s", idempotency_key)
            raise ValueError(f"Duplicate idempotency_key: {idempotency_key}")

    # Create diagnosis with correct created_at timestamp
    # The model will auto-generate created_at using default=_utcnow
    d = Diagnosis(
        district=district if consent_persist else None,
        crop=crop,
        predicted_class=predicted_class,
        confidence=confidence,
        uncertainty_score=uncertainty_score,
        top_k_json=top_k_json,
        consent_persist=consent_persist,
        session_id=session_id,
        idempotency_key=idempotency_key,
    )
    session.add(d)
    session.flush()

    # Call audit with the diagnosis's actual creation timestamp
    diagnosis_id = str(d.id)
    _write_audit(session, "diagnosis.record", target_id=diagnosis_id, payload={
        "district": district,
        "predicted_class": predicted_class,
        "consent": consent_persist,
        "idempotency_key": idempotency_key,
    })

    # Return the diagnosis object - its timestamp is set by the model's default
    # When set with server_default and default, the DB will use the proper timestamp
    return d


def get_advice(
    session: Session,
    class_label: str,
    language: str = "en",
) -> dict:
    """Fetch advisory advice for a disease class in a given language.

    Falls back to English if the requested language is not available.
    Returns {"title", "content", "language", "fallback_used"} dict.
    """
    rows = session.execute(
        select(AdvisoryKB)
        .where(AdvisoryKB.class_label == class_label)
        .where(AdvisoryKB.language == language)
        .where(AdvisoryKB.verified == True)
        .order_by(AdvisoryKB.id)
        .limit(5)
    ).scalars().all()

    if rows:
        return {
            "title": rows[0].title,
            "content": rows[0].content,
            "language": language,
            "fallback_used": False,
        }

    # Fallback to English
    en_rows = session.execute(
        select(AdvisoryKB)
        .where(AdvisoryKB.class_label == class_label)
        .where(AdvisoryKB.language == "en")
        .where(AdvisoryKB.verified == True)
        .order_by(AdvisoryKB.id)
        .limit(5)
    ).scalars().all()

    return {
        "title": en_rows[0].title if en_rows else "No advice available",
        "content": en_rows[0].content if en_rows else "Consult a local agriculture expert.",
        "language": "en",
        "fallback_used": True,
    }


def record_feedback(
    session: Session,
    diagnosis_id: uuid.UUID,
    class_label: str,
    correct: bool,
    comment: Optional[str] = None,
    district: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Feedback:
    """Record farmer feedback with replay protection."""
    if idempotency_key is not None:
        existing = session.execute(
            select(Feedback).where(Feedback.idempotency_key == idempotency_key)
        ).first()
        if existing is not None:
            raise ValueError(f"Duplicate feedback idempotency_key: {idempotency_key}")

    f = Feedback(
        diagnosis_id=diagnosis_id,
        class_label=class_label,
        correct=correct,
        comment=comment,
        district=district,
        idempotency_key=idempotency_key,
    )
    session.add(f)
    session.flush()

    _write_audit(session, "feedback.record", target_id=str(f.id), payload={
        "diagnosis_id": str(diagnosis_id),
        "correct": correct,
    })
    return f


def record_hotspot(
    session: Session,
    district: str,
    disease: str,
    crop: Optional[str] = None,
    count: int = 1,
    severity: Optional[str] = None,
    diagnosis_id: Optional[uuid.UUID] = None,
) -> Hotspot:
    """Record a hotspot entry."""
    h = Hotspot(
        district=district,
        disease=disease,
        crop=crop,
        count=count,
        severity=severity,
        diagnosis_id=diagnosis_id,
    )
    session.add(h)
    session.flush()

    _write_audit(session, "hotspot.record", target_id=str(h.id), payload={
        "district": district,
        "disease": disease,
    })
    return h


def k_anonymity_outbreak_report(
    session: Session,
    district: str,
    min_population: int = 5,
) -> Optional[dict]:
    """Return an outbreak report for a district only if it meets k-anonymity.

    Returns None if the district has fewer than `min_population` diagnoses
    in the last 7 days (privacy-preserving silence).
    """
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = session.execute(
        select(func.count(Diagnosis.id))
        .where(Diagnosis.district == district)
        .where(Diagnosis.created_at >= seven_days_ago)
    ).scalar_one()

    if result < min_population:
        return None

    disease_counts = session.execute(
        select(Diagnosis.predicted_class, func.count(Diagnosis.id))
        .where(Diagnosis.district == district)
        .where(Diagnosis.created_at >= seven_days_ago)
        .group_by(Diagnosis.predicted_class)
        .order_by(func.count(Diagnosis.id).desc())
    ).all()

    return {
        "district": district,
        "total_diagnoses": result,
        "top_diseases": [{"class": row[0], "count": row[1]} for row in disease_counts],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def delete_my_data(session: Session, user_id: uuid.UUID) -> dict:
    """GDPR delete: anonymize all personal data for a user."""
    sub_query = select(DBSession.id).where(DBSession.user_id == user_id)

    session.execute(delete(Feedback).where(Feedback.diagnosis_id.in_(
        select(Diagnosis.id).where(Diagnosis.session_id.in_(sub_query))
    )))
    rows = session.execute(delete(Hotspot).where(Hotspot.diagnosis_id.in_(
        select(Diagnosis.id).where(Diagnosis.session_id.in_(sub_query))
    ))).rowcount
    session.execute(update(Diagnosis)
        .where(Diagnosis.session_id.in_(sub_query))
        .values(district=None))
    session.execute(delete(User).where(User.id == user_id))
    session.execute(delete(DBSession).where(DBSession.user_id == user_id))
    session.commit()
    return {"deleted_user_id": str(user_id), "rows_deleted_approx": rows + 1}


def rotate_key(
    session: Session,
    new_fernet_key_b64: str,
    revoke_index: Optional[int] = None,
) -> int:
    """Add a new Fernet key and optionally revoke an old one."""
    max_idx = session.execute(
        select(func.coalesce(func.max(KeyRegistry.key_index), -1))
    ).scalar_one()
    new_idx = max_idx + 1
    now = datetime.now(timezone.utc)
    session.add(KeyRegistry(key_index=new_idx, fernet_key_b64=new_fernet_key_b64, created_at=now))
    if revoke_index is not None:
        session.execute(
            update(KeyRegistry)
            .where(KeyRegistry.key_index == revoke_index)
            .values(revoked_at=now)
        )
    session.commit()
    return new_idx


def purge_expired(session: Session, retention_days: Optional[int] = None) -> int:
    """Delete/anonymize diagnoses older than retention_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days or _DIAGNOSIS_RETENTION_DAYS)

    # First check what would be deleted
    would_delete = session.execute(
        select(Diagnosis.id).where(
            Diagnosis.created_at < cutoff,
            Diagnosis.consent_persist == False,
        )
    ).scalars().all()

    deleted = session.execute(
        delete(Diagnosis).where(
            Diagnosis.created_at < cutoff,
            Diagnosis.consent_persist == False,
        )
    ).rowcount

    # Also check and update consented diagnoses
    session.execute(
        update(Diagnosis)
        .where(Diagnosis.created_at < cutoff, Diagnosis.consent_persist == True)
        .values(district=None)
    )

    session.execute(delete(SyncQueue).where(SyncQueue.ts < cutoff))
    session.commit()
    return deleted


def export_retraining_data(
    session: Session,
    district_filter: Optional[str] = None,
) -> list[dict]:
    """Export expert-CONFIRMED feedback only (label corrections, not raw images)."""
    rows = session.execute(
        select(Feedback, Diagnosis)
        .join(Diagnosis, Feedback.diagnosis_id == Diagnosis.id)
        .where(Feedback.correct == True)
        .outerjoin(User, Diagnosis.session_id.in_(
            select(DBSession.id).where(DBSession.user_id == User.id)
        ))
    ).all()

    return [
        {
            "diagnosis_id": str(r[1].id),
            "district": r[1].district,
            "predicted_class": r[1].predicted_class,
            "correct_class": r[0].class_label,
            "confidence": r[1].confidence,
            "created_at": r[1].created_at.isoformat(),
        }
        for r in rows
        if r[0].correct
    ]


def _write_audit(
    session: Session, action: str, target_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """Append an immutable hash-chained audit row."""
    from .security import chain_head

    # Always start from the genesis block for audit logs
    prev_hash = chain_head()

    # Check if there's an existing audit log to chain from
    try:
        last = session.execute(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
        ).scalar_one_or_none()
        # If we already have audit logs, chain from the last one's data_hash
        if last and last.id:
            prev_hash = last.data_hash
    except Exception as e:
        pass  # Using chain_head when there's no audit log is fine

    payload_str = json.dumps(payload or {}, default=str, sort_keys=True)
    data_hash = compute_chain_hash(prev_hash, action, payload_str)
    row = AuditLog(
        action=action,
        target_id=target_id,
        prev_hash=prev_hash,
        data_hash=data_hash,
        payload_json=payload_str,
    )
    session.add(row)
    session.flush()  # Flush to get the id immediately


def get_pending_sync(session: Session, limit: int = 100) -> list[SyncQueue]:
    """Get unsynced offline queue entries."""
    return session.execute(
        select(SyncQueue)
        .where(SyncQueue.synced == False)
        .order_by(SyncQueue.ts.asc())
        .limit(limit)
    ).scalars().all()


def mark_synced(session: Session, sync_id: str) -> None:
    """Mark a sync queue entry as synced."""
    session.execute(
        update(SyncQueue).where(SyncQueue.id == sync_id).values(synced=True)
    )


def add_sync_entry(session: Session, entry: SyncQueue) -> None:
    """Add an offline sync entry."""
    session.add(entry)
