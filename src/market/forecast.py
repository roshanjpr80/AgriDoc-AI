"""Simple price forecasting and sell/wait signals.

We start with a lightweight baseline (rolling average + momentum) rather than
a heavy XGBoost model. It runs offline on cached prices, needs no training,
and gives a clear "sell now / hold / wait" signal. When enough historical
data is available, a small XGBoost regressor can replace the baseline; the
interface stays the same.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from src.market.prices import PriceRecord


def _series(records: List[PriceRecord]) -> List[float]:
    """Extract modal prices in chronological order."""
    return [r.modal_price for r in sorted(records, key=lambda r: r.ts)]


def price_forecast(
    records: List[PriceRecord],
    horizon_days: int = 7,
) -> dict:
    """Forecast the modal price *horizon_days* ahead.

    Uses a rolling 7-day average with momentum. Returns the forecast, the
    trend, and the confidence (0-1). Confidence is low when the series is
    short or flat — the farmer should not over-trust a noisy signal.
    """
    prices = _series(records)
    if not prices:
        return {"forecast": 0.0, "trend": "unknown", "confidence": 0.0, "method": "none"}

    window = min(7, len(prices))
    recent = prices[-window:]
    avg = sum(recent) / len(recent)

    if len(prices) >= 2:
        momentum = (prices[-1] - prices[-2]) / max(prices[-2], 1e-6)
    else:
        momentum = 0.0

    forecast = avg * (1 + momentum)

    if momentum > 0.02:
        trend = "rising"
    elif momentum < -0.02:
        trend = "falling"
    else:
        trend = "stable"

    # Confidence rises with the amount of data, falls with volatility.
    volatility = 0.0
    if len(recent) >= 2:
        mean = sum(recent) / len(recent)
        variance = sum((p - mean) ** 2 for p in recent) / len(recent)
        volatility = (variance ** 0.5) / max(mean, 1e-6)

    confidence = min(1.0, len(prices) / 30.0) * max(0.0, 1.0 - volatility)
    return {
        "forecast": round(forecast, 2),
        "trend": trend,
        "confidence": round(confidence, 2),
        "method": "rolling_average_momentum",
        "volatility": round(volatility, 3),
    }


def simple_signal(
    records: List[PriceRecord],
    forecast: dict,
    treatment_needed: bool = True,
) -> Tuple[str, str]:
    """Return (recommendation, reason) for the farmer.

    Logic:
      * If treatment is urgent and prices are falling -> treat now, sell later.
      * If prices are rising and treatment can wait -> hold.
      * If prices are stable -> sell now to avoid spoilage.
    """
    trend = forecast.get("trend", "unknown")
    confidence = forecast.get("confidence", 0.0)
    if confidence < 0.3:
        return "wait", "not enough price data — check the mandi again tomorrow"

    if treatment_needed:
        if trend == "rising":
            return "hold", "prices are rising; treat now and sell in a few days for more profit"
        if trend == "falling":
            return "sell_now", "prices are falling; sell what is harvestable now and treat the rest"
        return "sell_now", "prices are stable; sell now to avoid spoilage, then treat remaining crops"
    else:
        if trend == "rising":
            return "hold", "no urgent treatment and prices are rising — hold for better price"
        return "wait", "no urgent treatment; monitor prices and treat only if they fall"