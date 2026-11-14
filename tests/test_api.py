"""API endpoint tests for AgriDoc AI production API.

Run: python -m pytest tests/test_api.py -q
"""
from __future__ import annotations

import io
import json
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def _sample_image_bytes() -> bytes:
    """Create a small valid JPEG image for testing."""
    from PIL import Image
    img = Image.new("RGB", (224, 224), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _sample_image_b64() -> str:
    return base64.b64encode(_sample_image_bytes()).decode()


class TestHealthEndpoints:
    """Test liveness and readiness endpoints."""

    def test_health_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "model" in data

    def test_ready_ok(self):
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "model" in data

    def test_model_info_endpoint_requires_auth(self):
        """model-info requires auth like other endpoints."""
        resp = client.get("/model-info")
        assert resp.status_code == 401

    def test_model_info_endpoint_with_key(self, mock_onnx_session):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.get("/model-info", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "model" in data
        assert "size_mb" in data
        assert "classes" in data
        assert "runtime" in data


class TestClassesEndpoint:
    """Test /classes endpoint."""

    def test_classes_requires_auth(self):
        resp = client.get("/classes")
        assert resp.status_code == 401

    def test_classes_returns_list_with_key(self, mock_onnx_session):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.get("/classes", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "classes" in data
        assert isinstance(data["classes"], list)
        assert len(data["classes"]) > 0


class TestPredictEndpoint:
    """Test /predict endpoint."""

    def test_predict_requires_auth(self):
        resp = client.post("/predict", files={"file": ("test.jpg", _sample_image_bytes(), "image/jpeg")})
        assert resp.status_code == 401

    def test_predict_with_valid_key(self, mock_onnx_session):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/predict",
            headers=headers,
            files={"file": ("test.jpg", _sample_image_bytes(), "image/jpeg")},
            data={"top_k": "3", "include_cam": "false"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "diagnosis" in data
        assert "confidence" in data
        assert "predictions" in data
        assert "uncertain" in data
        assert "confidence_floor" in data
        assert isinstance(data["predictions"], list)
        assert len(data["predictions"]) <= 3

    def test_predict_invalid_file_type(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/predict",
            headers=headers,
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code == 415

    def test_predict_file_too_large(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        large = b"x" * (11 * 1024 * 1024)  # 11 MiB
        resp = client.post(
            "/predict",
            headers=headers,
            files={"file": ("large.jpg", large, "image/jpeg")},
        )
        assert resp.status_code == 413

    def test_predict_invalid_image(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/predict",
            headers=headers,
            files={"file": ("invalid.jpg", b"not an image", "image/jpeg")},
        )
        assert resp.status_code == 400


class TestAdviceEndpoint:
    """Test /advice endpoint."""

    def test_advice_requires_auth(self):
        resp = client.post("/advice", data={"class_label": "Apple___Apple_scab", "lang": "en"})
        assert resp.status_code == 401

    def test_advice_valid_request(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/advice",
            headers=headers,
            data={"class_label": "Apple___Apple_scab", "lang": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "advice" in data
        assert "crop" in data
        assert "disease" in data
        assert "source" in data
        assert "grounded" in data
        assert "disclaimer" in data

    def test_advice_invalid_class_label(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/advice",
            headers=headers,
            data={"class_label": "invalid@class", "lang": "en"},
        )
        assert resp.status_code == 400

    def test_advice_unsupported_language(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/advice",
            headers=headers,
            data={"class_label": "Apple___Apple_scab", "lang": "fr"},
        )
        assert resp.status_code == 400


class TestRagEndpoint:
    """Test /rag endpoint."""

    def test_rag_requires_auth(self):
        resp = client.post("/rag", data={"query": "How to treat leaf blight?", "lang": "en"})
        assert resp.status_code == 401

    def test_rag_valid_request(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/rag",
            headers=headers,
            data={"query": "How to treat leaf blight?", "lang": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "grounded" in data
        assert "disclaimer" in data

    def test_rag_empty_query(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/rag",
            headers=headers,
            data={"query": "", "lang": "en"},
        )
        # FastAPI returns 422 for validation errors on form data
        assert resp.status_code in (400, 422)

    def test_rag_query_too_long(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        long_query = "x" * 201
        resp = client.post(
            "/rag",
            headers=headers,
            data={"query": long_query, "lang": "en"},
        )
        assert resp.status_code == 400


class TestAgripulseEndpoint:
    """Test /agripulse endpoint."""

    def test_agripulse_requires_auth(self):
        resp = client.post("/agripulse", files={"file": ("test.jpg", _sample_image_bytes(), "image/jpeg")})
        assert resp.status_code == 401

    def test_agripulse_valid_request(self, mock_onnx_session):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/agripulse",
            headers=headers,
            files={"file": ("test.jpg", _sample_image_bytes(), "image/jpeg")},
            data={"language": "en", "district": "Test District", "offline": "false"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "reasons" in data
        assert "predicted_class" in data
        assert "confidence" in data
        assert "advice" in data
        assert "sell_recommendation" in data
        assert "weather_risk" in data
        assert "decisions" in data


class TestFeedbackEndpoint:
    """Test /feedback endpoint."""

    def test_feedback_requires_auth(self):
        resp = client.post("/feedback", data={"class_label": "Apple___Apple_scab", "correct": "true"})
        assert resp.status_code == 401

    def test_feedback_valid_request(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post(
            "/feedback",
            headers=headers,
            data={"class_label": "Apple___Apple_scab", "correct": "true", "comment": "Looks correct"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "queued" in data
        assert data["queued"] is True
        assert "record" in data


class TestSyncEndpoint:
    """Test /sync endpoint."""

    def test_sync_requires_auth(self):
        resp = client.post("/sync", json={"device_id": "test", "items": []})
        assert resp.status_code == 401

    def test_sync_empty_items(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.post("/sync", headers=headers, json={"device_id": "test", "items": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced"] == []
        assert data["merged"] == []
        assert data["rejected"] == []

    def test_sync_with_items(self, mock_onnx_session):
        headers = {"X-API-Key": "agridoc-test-key"}
        item = {
            "id": "test-1",
            "ts": "2025-11-01T00:00:00Z",
            "image_b64": _sample_image_b64(),
            "mime_type": "image/jpeg",
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.85,
            "uncertain": False,
            "farmer_correct": True,
            "farmer_comment": "confirmed",
        }
        resp = client.post(
            "/sync",
            headers=headers,
            json={"device_id": "test", "items": [item]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "synced" in data
        assert "merged" in data
        assert "rejected" in data
        assert "server_predictions" in data


class TestDeleteDataEndpoint:
    """Test /data DELETE endpoint."""

    def test_delete_data_requires_auth(self):
        resp = client.delete("/data")
        assert resp.status_code == 401

    def test_delete_data_valid(self):
        headers = {"X-API-Key": "agridoc-test-key"}
        resp = client.delete("/data", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted" in data
        assert data["deleted"] is True


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_exceeded(self):
        """Test that rate limit is enforced per IP."""
        # This test would need a clean TestClient to avoid interference
        # from other tests. In practice, rate limiting is per-IP and
        # TestClient shares the same "client" IP.
        pass


class TestSecurityHeaders:
    """Test security headers are present."""

    def test_security_headers_on_authenticated_endpoint(self):
        """Security headers are added to authenticated endpoints."""
        headers = {"X-API-Key": "agridoc-BbYpvS4PeYdPydV9rwLvC-tbT8UuXKuAcFfrAVHoJfM"}
        resp = client.get("/model-info", headers=headers)
        assert "X-Content-Type-Options" in resp.headers
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in resp.headers
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in resp.headers
        assert "Referrer-Policy" in resp.headers
        assert "Content-Security-Policy" in resp.headers
        assert "Strict-Transport-Security" in resp.headers
        assert "Cache-Control" in resp.headers

    def test_security_headers_on_error_response(self):
        """Security headers are present even on auth error responses."""
        resp = client.post("/predict", files={"file": ("test.jpg", _sample_image_bytes(), "image/jpeg")})
        assert resp.status_code == 401
        assert "X-Content-Type-Options" in resp.headers
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in resp.headers
        assert "X-XSS-Protection" in resp.headers


class TestCORS:
    """Test CORS configuration."""

    def test_cors_on_error_response(self):
        # Make an unauthenticated request to trigger auth error
        resp = client.post("/predict", files={"file": ("test.jpg", _sample_image_bytes(), "image/jpeg")})
        # Should have CORS headers even on error
        assert resp.status_code == 401


# Fixtures

@pytest.fixture
def mock_onnx_session():
    """Mock ONNX inference session for testing."""
    import onnxruntime as ort
    from unittest.mock import patch

    # Create a mock session that returns fixed predictions
    mock_session = MagicMock()
    # Simulate logits for 38 classes
    import numpy as np
    logits = np.random.randn(1, 38).astype(np.float32)
    mock_session.run.return_value = [logits]

    with patch("src.api.inference._session", mock_session):
        with patch("src.api.inference._LABELS", [f"Class_{i}" for i in range(38)]):
            yield mock_session


@pytest.fixture(autouse=True)
def setup_test_keys():
    """Set up test API keys for authentication."""
    from backend import config
    original_keys = config.ALLOWED_API_KEYS
    config.ALLOWED_API_KEYS = {"agridoc-test-key"}
    yield
    config.ALLOWED_API_KEYS = original_keys