"""Weather / risk Agent node for AgriPulse.

Fetches a public forecast for the farmer's district and turns it into a
treatment-risk signal: rain in the next 48h means spraying should wait
(wet leaves dilute fungicide and run-off wastes it), while a dry spell means
treat now.

Data source: Open-Meteo (open, free, no auth, CC BY 4.0). Cached to disk
for 24h so the app works offline.
"""
from __future__ import annotations

import logging
from typing import Optional

from .state import AgriPulseState

log = logging.getLogger("agridoc.agents.weather")


def _tool(lat: float, lon: float, offline: bool = False) -> dict:
    """Return {rain_next_48h_mm, risk, forecast} for a lat/lon."""
    if offline:
        return {"rain_next_48h_mm": 0.0, "risk": "unknown", "forecast": "offline"}
    try:
        import json
        import urllib.parse
        import httpx

        url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "precipitation",
                    "forecast_hours": 48,
                    "timezone": "auto",
                }
            )
        )
        resp = httpx.get(url, headers={"User-Agent": "AgriDocAI/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        precip = data.get("hourly", {}).get("precipitation", []) or []
        total = sum(p for p in precip if isinstance(p, (int, float)))
        if total >= 15:
            risk = "high"
        elif total >= 5:
            risk = "medium"
        else:
            risk = "low"
        return {
            "rain_next_48h_mm": round(total, 1),
            "risk": risk,
            "forecast": f"{total:.1f}mm rain in 48h",
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("weather fetch failed: %s", exc)
        return {"rain_next_48h_mm": 0.0, "risk": "unknown", "forecast": "unavailable"}


def node(state: AgriPulseState) -> AgriPulseState:
    """LangGraph node: assess weather risk for treatment timing."""
    district = state.get("district", "")
    lat, lon = _district_coords(district)
    offline = state.get("offline", False)
    result = _tool(lat, lon, offline=offline)
    state["weather_risk"] = result["risk"]
    state["rain_forecast"] = result["forecast"]
    state["decisions"].append(
        f"weather: {district} risk={state['weather_risk']} ({state['rain_forecast']})"
    )
    return state


def _district_coords(district: str) -> tuple[float, float]:
    """Look up district centroid coordinates. Falls back to Delhi."""
    from src.privacy.location import DISTRICT_CENTROIDS

    if district in DISTRICT_CENTROIDS:
        return DISTRICT_CENTROIDS[district]
    # Try a loose match on the state prefix.
    for key, coords in DISTRICT_CENTROIDS.items():
        if district and district.split("_")[0] in key:
            return coords
    return (28.6139, 77.2090)  # Delhi fallback