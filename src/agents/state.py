"""Typed state for the AgriPulse LangGraph workflow.

The state flows through: diagnose -> advise -> market -> weather -> coordinate.
Every node appends to ``decisions`` so the final plan is fully auditable.
"""
from __future__ import annotations

from typing import Annotated, Dict, List, Optional, Sequence

from typing_extensions import TypedDict


def _extend(left: Optional[List[str]], right: Sequence[str]) -> List[str]:
    """Reducer: append *right* to *left* (used for the decisions log)."""
    if left is None:
        return list(right)
    return left + list(right)


class AgriPulseState(TypedDict, total=False):
    """All fields are optional so a node can start from a partial state."""

    # --- Input ---
    image_bytes: bytes
    mime_type: str
    language: str
    district: str
    crop_hint: Optional[str]

    # --- Diagnosis ---
    predicted_class: str
    confidence: float
    uncertain: bool
    gradcam_url: Optional[str]

    # --- Advice ---
    advice_text: str
    treatment_options: List[str]
    safety_warnings: List[str]
    call_expert: bool

    # --- Market ---
    crop_prices: Dict[str, float]
    price_trend: str  # "rising" | "falling" | "stable"
    sell_recommendation: str

    # --- Weather / risk ---
    weather_risk: str  # "low" | "medium" | "high"
    rain_forecast: str

    # --- Coordination ---
    plan: str
    reasons: List[str]
    decisions: Annotated[Optional[List[str]], _extend]


def initial_state(
    image_bytes: bytes,
    language: str = "en",
    district: str = "",
    crop_hint: Optional[str] = None,
) -> AgriPulseState:
    """Build the starting state for a farmer query."""
    return {
        "image_bytes": image_bytes,
        "mime_type": "image/jpeg",
        "language": language,
        "district": district,
        "crop_hint": crop_hint,
        "decisions": [],
    }