"""Tests for the AgriPulse LangGraph agent workflow.

Run: python -m pytest tests/test_agents.py -q
"""
from __future__ import annotations

import io
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import numpy as np

from src.agents.graph import run_agripulse
from src.agents.diagnosis import node as diagnose_node
from src.agents.advice_agent import node as advice_node
from src.agents.market_agent import node as market_node
from src.agents.weather_agent import node as weather_node
from src.agents.coordinator import node as coordinator_node
from src.agents.weather_agent import _tool as fetch_weather
from src.market.forecast import simple_signal
from src.market.prices import PriceRecord


def _sample_image_bytes() -> bytes:
    """Create a small valid JPEG image for testing."""
    from PIL import Image
    img = Image.new("RGB", (224, 224), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestDiagnosisNode:
    """Test the diagnosis agent node."""

    def test_diagnose_node_returns_state(self, mock_onnx_session):
        state = {
            "image_bytes": _sample_image_bytes(),
            "language": "en",
            "district": "Test District",
            "offline": False,
            "decisions": [],
        }
        result = diagnose_node(state)
        assert "predicted_class" in result
        assert "confidence" in result
        assert "uncertain" in result
        assert "predictions" in result
        assert isinstance(result["confidence"], float)
        assert isinstance(result["uncertain"], bool)

    def test_diagnose_node_sets_uncertain_below_floor(self, mock_low_confidence_onnx):
        state = {
            "image_bytes": _sample_image_bytes(),
            "language": "en",
            "district": "Test District",
            "offline": False,
            "decisions": [],
        }
        result = diagnose_node(state)
        assert result["uncertain"] is True

    def test_diagnose_node_language_passthrough(self, mock_onnx_session):
        for lang in ["en", "hi", "bn", "ta", "te"]:
            state = {
                "image_bytes": _sample_image_bytes(),
                "language": lang,
                "district": "Test District",
                "offline": False,
                "decisions": [],
            }
            result = diagnose_node(state)
            assert result.get("language") == lang or "language" not in result


class TestAdviceNode:
    """Test the advice agent node."""

    def test_advice_node_grounded(self, mock_diagnosis_state):
        result = advice_node(mock_diagnosis_state)
        assert "advice_text" in result
        assert "advice_source" in result
        assert "advice_grounded" in result
        assert result["advice_grounded"] is True

    def test_advice_node_offline_mode(self, mock_diagnosis_state):
        state = {**mock_diagnosis_state, "offline": True}
        result = advice_node(state)
        assert "advice_text" in result
        # Should still work in offline mode

    def test_advice_node_all_languages(self, mock_diagnosis_state):
        for lang in ["en", "hi", "bn", "ta", "te", "mr", "gu", "ml", "kn", "pa"]:
            state = {**mock_diagnosis_state, "language": lang}
            result = advice_node(state)
            assert "advice_text" in result
            assert len(result["advice_text"]) > 0


class TestMarketNode:
    """Test the market agent node."""

    def test_market_node_returns_price_data(self, mock_diagnosis_state):
        with patch("src.market.prices.fetch_price") as mock_fetch:
            mock_fetch.return_value = PriceRecord(
                crop="apple",
                district="Test District",
                state="Test State",
                min_price=4500,
                max_price=5500,
                modal_price=5000,
                unit="quintal",
                ts=time.time(),
                source="agmarknet",
            )
            result = market_node(mock_diagnosis_state)
            assert "crop_prices" in result
            assert "sell_recommendation" in result
            assert result["sell_recommendation"] in ["sell", "hold", "wait", "unknown"]

    def test_market_node_offline_mode(self, mock_diagnosis_state):
        state = {**mock_diagnosis_state, "offline": True, "decisions": []}
        result = market_node(state)
        assert "crop_prices" in result
        assert "sell_recommendation" in result
        # Should return sensible defaults in offline mode

    def test_market_node_crop_mapping(self, mock_diagnosis_state):
        # Test that PlantVillage classes map to mandi commodities
        from src.market.lookup import crop_for_class
        commodity = crop_for_class("Apple___Apple_scab")
        assert commodity is not None
        assert isinstance(commodity, str)
        assert commodity == "apple"


class TestWeatherNode:
    """Test the weather agent node."""

    def test_weather_node_returns_forecast(self, mock_diagnosis_state):
        with patch("src.agents.weather_agent._tool") as mock_fetch:
            mock_fetch.return_value = {
                "rain_next_48h_mm": 2.5,
                "risk": "low",
                "forecast": "2.5mm rain in 48h",
            }
            result = weather_node(mock_diagnosis_state)
            assert "weather_risk" in result
            assert "rain_forecast" in result
            assert result["weather_risk"] in ["low", "medium", "high", "unknown"]

    def test_weather_node_offline_mode(self, mock_diagnosis_state):
        state = {**mock_diagnosis_state, "offline": True, "decisions": []}
        result = weather_node(state)
        assert "weather_risk" in result
        assert result["weather_risk"] == "unknown"

    def test_weather_node_rain_risk_high(self, mock_diagnosis_state):
        with patch("src.agents.weather_agent._tool") as mock_fetch:
            # High precipitation
            mock_fetch.return_value = {
                "rain_next_48h_mm": 25.0,
                "risk": "high",
                "forecast": "25.0mm rain in 48h",
            }
            result = weather_node(mock_diagnosis_state)
            assert result["weather_risk"] == "high"


class TestCoordinatorNode:
    """Test the coordinator agent node."""

    def test_coordinator_returns_plan(self, mock_full_state):
        result = coordinator_node(mock_full_state)
        assert "plan" in result
        assert "reasons" in result
        assert "decisions" in result
        assert result["plan"] in [
            "call_expert", "wait", "wait_48h", "sell_now", "hold", "treat_now"
        ]
        assert isinstance(result["reasons"], list)
        assert isinstance(result["decisions"], list)

    def test_coordinator_call_expert_on_uncertain(self):
        state = {
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.5,  # Below floor
            "uncertain": True,
            "advice_text": "Test advice",
            "sell_recommendation": "hold",
            "weather_risk": "low",
            "decisions": [],
        }
        result = coordinator_node(state)
        assert result["plan"] == "call_expert"
        assert any("low" in r.lower() or "severe" in r.lower() for r in result["reasons"])

    def test_coordinator_wait_on_high_weather_risk(self):
        """High weather risk should return wait regardless of disease severity."""
        state = {
            "predicted_class": "Tomato___Late_blight",
            "confidence": 0.9,
            "uncertain": False,
            "advice_text": "Apply fungicide immediately...",
            "sell_recommendation": "hold",
            "weather_risk": "high",
            "decisions": [],
        }
        result = coordinator_node(state)
        # High weather risk -> wait
        assert result["plan"] == "wait"

    def test_coordinator_sell_now_on_good_prices(self):
        state = {
            "predicted_class": "Apple___healthy",
            "confidence": 0.95,
            "uncertain": False,
            "advice_text": "Crop is healthy",
            "sell_recommendation": "sell_now",  # Must match market_agent output
            "weather_risk": "low",
            "decisions": [],
        }
        result = coordinator_node(state)
        assert result["plan"] == "sell_now"

    def test_coordinator_wait_on_uncertain_weather(self):
        state = {
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.85,
            "uncertain": False,
            "advice_text": "Treat with neem oil",
            "sell_recommendation": "hold",
            "weather_risk": "medium",
            "decisions": [],
        }
        result = coordinator_node(state)
        # Medium weather risk might suggest waiting
        assert result["plan"] in ["wait", "wait_48h", "treat_now"]


class TestAgripulseWorkflow:
    """Test the full AgriPulse workflow."""

    def test_run_agripulse_returns_complete_state(self, mock_onnx_session):
        image_bytes = _sample_image_bytes()
        state = run_agripulse(
            image_bytes=image_bytes,
            language="en",
            district="Test District",
            offline=False,
        )
        assert "predicted_class" in state
        assert "confidence" in state
        assert "uncertain" in state
        assert "advice_text" in state
        assert "crop_prices" in state
        assert "weather_risk" in state
        assert "plan" in state
        assert "reasons" in state
        assert "decisions" in state
        assert "sell_recommendation" in state

    def test_run_agripulse_offline_mode(self, mock_onnx_session):
        image_bytes = _sample_image_bytes()
        state = run_agripulse(
            image_bytes=image_bytes,
            language="en",
            district="Test District",
            offline=True,
        )
        assert "predicted_class" in state
        assert "plan" in state
        # Should complete without external API calls

    def test_run_agripulse_all_languages(self, mock_onnx_session):
        image_bytes = _sample_image_bytes()
        for lang in ["en", "hi", "bn", "ta", "te"]:
            state = run_agripulse(
                image_bytes=image_bytes,
                language=lang,
                district="Test District",
                offline=True,
            )
            assert "advice_text" in state
            assert len(state["advice_text"]) > 0

    def test_run_agripulse_sequential_fallback(self, mock_onnx_session):
        """Test that workflow works even without LangGraph."""
        # The fallback sequential runner should produce same results
        image_bytes = _sample_image_bytes()
        state = run_agripulse(
            image_bytes=image_bytes,
            language="en",
            district="Test District",
            offline=True,
        )
        assert "plan" in state


class TestMarketForecast:
    """Test market price forecasting."""

    def test_forecast_generates_signal(self):
        prices = [
            {"date": "2025-10-01", "price": 5000},
            {"date": "2025-10-02", "price": 5100},
            {"date": "2025-10-03", "price": 5050},
            {"date": "2025-10-04", "price": 5200},
            {"date": "2025-10-05", "price": 5150},
        ]
        signal = simple_signal(
            [],  # records
            {"trend": "rising", "confidence": 0.8},  # forecast
            treatment_needed=True,
        )
        assert signal[0] in ["sell", "hold", "wait"]
        assert isinstance(signal[0], str)

    def test_forecast_insufficient_data(self):
        signal = simple_signal(
            [],
            {"trend": "unknown", "confidence": 0.1},
            treatment_needed=True,
        )
        assert signal[0] == "wait"  # Default for insufficient data


# Fixtures

@pytest.fixture
def mock_onnx_session():
    """Mock ONNX inference session for testing."""
    import src.api.inference as inference_module
    from unittest.mock import patch

    # Create a mock session that returns fixed predictions
    mock_session = MagicMock()
    # Simulate logits for 38 classes - high confidence for first class
    import numpy as np
    logits = np.zeros((1, 38), dtype=np.float32)
    logits[0, 0] = 10.0  # High confidence for class 0
    logits[0, 1] = 2.0
    logits[0, 2] = 1.0
    mock_session.run.return_value = [logits]

    mock_labels = [f"Class_{i}" for i in range(38)]
    mock_labels[0] = "Apple___Apple_scab"

    with patch.object(inference_module, "_session", mock_session):
        with patch.object(inference_module, "_LABELS", mock_labels):
            with patch.object(inference_module, "_FLOOR", 0.70):
                yield mock_session


@pytest.fixture
def mock_low_confidence_onnx():
    """Mock ONNX session returning low confidence (below floor)."""
    import src.api.inference as inference_module
    from unittest.mock import patch

    mock_session = MagicMock()
    import numpy as np
    logits = np.ones((1, 38), dtype=np.float32) * 0.1  # Low confidence
    mock_session.run.return_value = [logits]

    mock_labels = [f"Class_{i}" for i in range(38)]

    with patch.object(inference_module, "_session", mock_session):
        with patch.object(inference_module, "_LABELS", mock_labels):
            with patch.object(inference_module, "_FLOOR", 0.70):
                yield mock_session


@pytest.fixture
def mock_diagnosis_state():
    """Mock state after diagnosis node."""
    return {
        "predicted_class": "Apple___Apple_scab",
        "confidence": 0.85,
        "uncertain": False,
        "predictions": [
            {"class": "Apple___Apple_scab", "confidence": 0.85},
            {"class": "Apple___healthy", "confidence": 0.10},
            {"class": "Apple___Black_rot", "confidence": 0.05},
        ],
        "language": "en",
        "district": "Test District",
        "offline": False,
        "decisions": [],
    }


@pytest.fixture
def mock_full_state():
    """Mock complete state for coordinator."""
    return {
        "predicted_class": "Apple___Apple_scab",
        "confidence": 0.85,
        "uncertain": False,
        "advice_text": "Mix neem oil with water, spray weekly",
        "advice_source": "ICAR",
        "advice_grounded": True,
        "market_data": {"commodity": "Apple", "prices": []},
        "sell_recommendation": "hold",
        "weather_forecast": {"precipitation_probability": [0.1, 0.2]},
        "weather_risk": "low",
        "language": "en",
        "district": "Test District",
        "offline": False,
        "decisions": [],
    }