"""Market Agent node for AgriPulse.

Looks up the current mandi price for the diagnosed crop, forecasts the trend,
and recommends sell / hold / wait. Degrades gracefully offline.
"""
from __future__ import annotations

import logging

from .state import AgriPulseState
from src.market.lookup import crop_for_class
from src.market.prices import fetch_price
from src.market.forecast import price_forecast, simple_signal

log = logging.getLogger("agridoc.agents.market")


def _tool(crop: str, district: str) -> dict:
    """Return {record, forecast, recommendation, reason} for a crop."""
    record = fetch_price(crop, district=district)
    forecast = price_forecast([record] if record else [])
    recommendation, reason = simple_signal(
        [record] if record else [],
        forecast,
        treatment_needed=True,
    )
    return {
        "record": record,
        "forecast": forecast,
        "recommendation": recommendation,
        "reason": reason,
    }


def node(state: AgriPulseState) -> AgriPulseState:
    """LangGraph node: fetch prices and produce a sell/wait signal."""
    class_label = state.get("predicted_class", "")
    district = state.get("district", "")
    crop = crop_for_class(class_label) if class_label else ""
    if not crop:
        state["sell_recommendation"] = "unknown"
        state["decisions"].append("market: no crop known -> no price signal")
        return state

    try:
        result = _tool(crop, district)
    except Exception as exc:  # noqa: BLE001
        log.warning("market lookup failed: %s", exc)
        state["sell_recommendation"] = "unknown"
        state["decisions"].append(f"market: lookup failed ({exc}) -> no signal")
        return state

    record = result["record"]
    forecast = result["forecast"]
    state["crop_prices"] = (
        {crop: record.modal_price} if record else {}
    )
    state["price_trend"] = forecast.get("trend", "unknown")
    state["sell_recommendation"] = result["recommendation"]
    state["decisions"].append(
        f"market: {crop} trend={state['price_trend']} "
        f"-> {state['sell_recommendation']}"
    )
    return state