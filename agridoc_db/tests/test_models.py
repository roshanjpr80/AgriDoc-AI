"""Tests for agridoc_db models."""
import uuid
from datetime import datetime, timezone

from agridoc_db.models import AdvisoryKB, Diagnosis, Feedback


def test_diagnosis_create(session) -> None:
    d = Diagnosis(
        district="TestDistrict",
        predicted_class="Leaf_Blight",
        confidence=0.89,
        consent_persist=True,
        idempotency_key="idem-test-001",
    )
    session.add(d)
    session.flush()
    assert d.id is not None
    assert isinstance(d.id, uuid.UUID)
    assert d.created_at.tzinfo is not None


def test_diagnosis_no_district_without_consent(session) -> None:
    from agridoc_db.services import record_diagnosis
    d = record_diagnosis(session, "VisibleDistrict", "Healthy", 0.95, consent_persist=False)
    assert d.district is None


def test_advisory_fallback(session) -> None:
    session.add(AdvisoryKB(
        class_label="Leaf_Blight",
        language="en",
        title="Leaf Blight Care",
        content="English advice.",
    ))
    session.flush()
    from agridoc_db.services import get_advice
    result = get_advice(session, "Leaf_Blight", language="kn")
    assert result["language"] == "en"
    assert result["fallback_used"] is True


def test_outbreak_aggregate_unique_constraint(session) -> None:
    from agridoc_db.models import OutbreakAggregate
    ob1 = OutbreakAggregate(
        district="D1", disease="Blight", week_start=datetime.now(timezone.utc), count=10
    )
    session.add(ob1)
    session.flush()
    # Second row with same key should raise uniqueness error (SQLite)
    ob2 = OutbreakAggregate(
        district="D1", disease="Blight", week_start=ob1.week_start, count=20
    )
    session.add(ob2)
    try:
        session.flush()
        pytest.fail("Expected IntegrityError on duplicate unique constraint")
    except Exception as e:
        assert "UNIQUE constraint failed" in str(e) or "UNIQUE constraint" in str(e)
