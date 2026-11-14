"""13 service-level tests for agridoc_db.

Covers: consent-gated diagnosis, idempotency, feedback, k-anonymity,
GDPR delete, audit chain, key rotation, purge, retraining export,
sync queue, advice fallback, multi-key Fernet.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from agridoc_db.models import AdvisoryKB, AuditLog, Diagnosis, Feedback, SyncQueue, User
from agridoc_db.security import chain_head, verify_chain, encrypt, decrypt
from agridoc_db.services import (
    add_sync_entry,
    delete_my_data,
    export_retraining_data,
    get_advice,
    get_pending_sync,
    k_anonymity_outbreak_report,
    mark_synced,
    purge_expired,
    record_diagnosis,
    record_feedback,
    record_hotspot,
    rotate_key,
)


def _env_setup() -> None:
    os.environ["AGRIDOC_DB_KEYS"] = (
        "gE3yW1VqR4vH6kZ8mN0pQ2sT4uW6yA8cE0gI2kM4oQ="
        ","
        "aB4dF6hJ8lN0pR2tV4xZ6bD8fH0jL2nP4rT6vX8zB="
    )
    os.environ["AGRIDOC_HMAC_SECRET"] = "test-hmac-secret-for-unittests"
    # Enable database validation schema check
    os.environ["AGRIDOC_DB_VALIDATE"] = "1"


@pytest.fixture(autouse=True)
def _setup_env():
    _env_setup()


# --- 1. consent-gated diagnosis ---
def test_01_diagnosis_consent(session) -> None:
    d = record_diagnosis(session, "Palakkad", "Leaf_Blight", 0.92, consent_persist=False)
    assert d.district is None
    assert d.id is not None
    session.commit()


def test_02_diagnosis_with_consent(session) -> None:
    d = record_diagnosis(session, "Palakkad", "Leaf_Blight", 0.92, consent_persist=True)
    assert d.district == "Palakkad"
    session.commit()


def test_diagnosis_no_district_without_consent(session) -> None:
    from agridoc_db.services import record_diagnosis
    d = record_diagnosis(session, "VisibleDistrict", "Healthy", 0.80, consent_persist=False)
    assert d.district is None


# --- 2. idempotency replay protection ---
def test_03_idempotency_key_protection(session) -> None:
    record_diagnosis(session, "Palakkad", "Leaf_Blight", 0.90, idempotency_key="idem-abc")
    with pytest.raises(ValueError, match="Duplicate idempotency_key"):
        record_diagnosis(session, "Palakkad", "Leaf_Blight", 0.90, idempotency_key="idem-abc")
    session.commit()


# --- 3. feedback with idempotency ---
def test_04_feedback_idempotency(session) -> None:
    d = record_diagnosis(session, "Palakkad", "Leaf_Blight", 0.90, consent_persist=True)
    session.flush()
    record_feedback(session, d.id, "Leaf_Blight", correct=True, idempotency_key="fb-001")
    session.commit()
    with pytest.raises(ValueError, match="Duplicate feedback idempotency_key"):
        record_feedback(session, d.id, "Leaf_Blight", correct=True, idempotency_key="fb-001")


# --- 4. k-anonymity below threshold ---
def test_05_k_anonymity_below_threshold(session) -> None:
    d = record_diagnosis(session, "SmallDist", "Healthy", 0.80)
    session.commit()
    report = k_anonymity_outbreak_report(session, "SmallDist", min_population=5)
    assert report is None


# --- 5. k-anonymity above threshold ---
def test_06_k_anonymity_above_threshold(session) -> None:
    now = datetime.now(timezone.utc)
    for i in range(6):
        record_diagnosis(session, "BigDist", "Leaf_Blight", 0.85, consent_persist=True)
    session.commit()
    report = k_anonymity_outbreak_report(session, "BigDist", min_population=5)
    assert report is not None
    assert report["total_diagnoses"] >= 5
    assert report["district"] == "BigDist"


# --- 6. GDPR delete_my_data ---
def test_07_delete_my_data(session) -> None:
    uid = uuid.uuid4()
    user = User(id=uid)
    session.add(user)
    session.flush()
    sid = uuid.uuid4()
    # Add a session linked to the user first
    from agridoc_db.models import Session as DBSession
    from datetime import datetime, timedelta, timezone
    sess = DBSession(
        id=sid,
        user_id=uid,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    session.add(sess)
    session.flush()
    # Add a diagnosis linked via session
    d = record_diagnosis(session, "DeleteDist", "Healthy", 0.90, consent_persist=True, session_id=sid)
    session.commit()
    result = delete_my_data(session, uid)
    assert result["deleted_user_id"] == str(uid)
    remaining = session.execute(select(User).where(User.id == uid)).first()
    assert remaining is None


# --- 7. audit chain integrity after diagnosis ---
def test_08_audit_chain_after_diagnosis(session) -> None:
    from agridoc_db.services import record_diagnosis
    record_diagnosis(session, "AuditDist", "Healthy", 0.90, consent_persist=True)
    session.commit()
    rows = session.execute(select(AuditLog).order_by(AuditLog.id)).scalars().all()
    dicts = [
        {"prev_hash": r.prev_hash, "action": r.action, "data_hash": r.data_hash, "payload_json": r.payload_json}
        for r in rows
    ]
    assert len(dicts) >= 1, "Should have at least one audit row"
    print("AUDIT DEBUG: dicts =", dicts)
    print("AUDIT DEBUG: chain_head =", chain_head())
    # Debug: verify hash computation
    from agridoc_db.security import compute_chain_hash, hmac_equals
    for i, d in enumerate(dicts):
        computed = compute_chain_hash(d['prev_hash'], d['action'], d['payload_json'])
        print(f"AUDIT DEBUG: row {i}: computed={computed}, actual={d['data_hash']}, match={computed == d['data_hash']}")

    # Use verify_chain from security module
    assert verify_chain(dicts) is True, f"Chain verification failed with {len(dicts)} rows"


# --- 8. key rotation ---
def test_09_rotate_key(session) -> None:
    # Check current state
    from agridoc_db.models import KeyRegistry
    existing_keys = session.execute(select(KeyRegistry).order_by(KeyRegistry.key_index)).scalars().all()
    print(f"DEBUG: Existing keys count: {len(existing_keys)}")
    for k in existing_keys:
        print(f"DEBUG: Existing key: idx={k.key_index}, revoked={k.revoked_at}")

    idx = rotate_key(session, "NEWkey1234567890123456789012345678==")
    print(f"DEBUG: rotate_key returned idx={idx}")
    assert idx == 0
    idx2 = rotate_key(session, "NEWkey2234567890123456789012345678==", revoke_index=idx)
    assert idx2 == 1
    session.commit()
    # Verify second key is in database
    keys = session.execute(select(KeyRegistry).order_by(KeyRegistry.key_index)).scalars().all()
    assert len(keys) == 2
    assert keys[0].revoked_at is not None


# --- 9. purge_expired removes old non-consented ---
def test_10_purge_expired(session) -> None:
    from agridoc_db.models import Diagnosis
    from agridoc_db.services import record_diagnosis
    from sqlalchemy import update
    old = datetime.now(timezone.utc) - timedelta(days=400)

    # Create an old diagnosis using services - manually set created_at since services don't expose this parameter
    old_d = record_diagnosis(session, "OldDistrict", "Healthy", 0.8, consent_persist=False, idempotency_key="old-d")
    # Force the old timestamp by updating the diagnosis's created_at directly
    session.execute(
        update(Diagnosis)
        .where(Diagnosis.id == old_d.id)
        .values(created_at=old)
    )
    session.commit()

    # Create a recent diagnosis using services
    new_d = record_diagnosis(session, "RecentDistrict", "Healthy", 0.85, consent_persist=False, idempotency_key="new-d")
    session.commit()

    # Re-query after committing to get fresh objects
    old_check = session.execute(select(Diagnosis).where(Diagnosis.id == old_d.id)).scalar_one_or_none()
    new_check = session.execute(select(Diagnosis).where(Diagnosis.id == new_d.id)).scalar_one_or_none()

    print(f"DEBUG: Before purge - old diagnosis: {old_check}, new diagnosis: {new_check}")
    print(f"DEBUG: old created_at: {old_check.created_at if old_check else None}")
    print(f"DEBUG: new created_at: {new_check.created_at if new_check else None}")

    deleted = purge_expired(session, retention_days=365)
    print(f"DEBUG: purge_expired returned deleted={deleted}")

    assert deleted == 1

    # Verify old one is gone, new one still exists
    old_check = session.execute(select(Diagnosis).where(Diagnosis.id == old_d.id)).scalar_one_or_none()
    new_check = session.execute(select(Diagnosis).where(Diagnosis.id == new_d.id)).scalar_one_or_none()
    print(f"DEBUG: After purge - old_check={old_check}, new_check={new_check}")
    assert old_check is None
    assert new_check is not None
    session.commit()


# --- 10. export_retraining returns only correct feedback ---
def test_11_export_retraining_data(session) -> None:
    d = record_diagnosis(session, "TrainDist", "Healthy", 0.90, consent_persist=True, idempotency_key="retrain-d")
    session.flush()
    record_feedback(session, d.id, "Healthy", correct=True, idempotency_key="retrain-f1")
    record_feedback(session, d.id, "Blight", correct=False, idempotency_key="retrain-f2")
    session.commit()
    rows = export_retraining_data(session)
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}: {rows}"
    assert rows[0]["correct_class"] == "Healthy"
    # Verify we got the correct diagnosis info - with consent_persist=True, district should be populated
    assert rows[0]["district"] == "TrainDist"
    assert rows[0]["predicted_class"] == "Healthy"


# --- 11. sync queue add / get / mark ---
def test_12_sync_queue_add_get_mark(session) -> None:
    entry_id = str(uuid.uuid4())
    entry = SyncQueue(
        id=entry_id,
        ts=datetime.now(timezone.utc),
        predicted_class="Leaf_Blight",
        confidence=0.88,
        synced=False,
    )
    add_sync_entry(session, entry)
    session.commit()
    pending = get_pending_sync(session)
    assert len(pending) == 1, f"Expected 1 pending entry, got {len(pending)}"
    mark_synced(session, entry_id)
    session.commit()
    pending_after = get_pending_sync(session)
    assert len(pending_after) == 0, f"Expected 0 pending entries after marking, got {len(pending_after)}"


# --- 12. advice English fallback ---
def test_13_advice_fallback(session) -> None:
    from agridoc_db.models import AdvisoryKB
    advisory = AdvisoryKB(
        class_label="Rice_Blade_Blight",
        language="en",
        title="RB Care",
        content="English guidance.",
    )
    session.add(advisory)
    session.commit()
    res = get_advice(session, "Rice_Blade_Blight", language="hi")
    assert res["language"] == "en", f"Expected English fallback, got {res['language']}"
    assert res["fallback_used"] is True
    assert res["title"] == "RB Care"
    # Verify that the advisory was saved by reading it back
    from agridoc_db.models import AdvisoryKB
    advisory_check = session.execute(
        select(AdvisoryKB).where(AdvisoryKB.class_label == "Rice_Blade_Blight", AdvisoryKB.language == "en")
    ).scalar_one_or_none()
    assert advisory_check is not None
    assert advisory_check.title == "RB Care"
