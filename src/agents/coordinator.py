"""Coordinator Agent for AgriPulse.

Combines the diagnosis, advice, market, and weather signals into one simple
plan: "Treat now / wait / sell now / hold" with reasons. Also decides whether
to escalate to a human agriculture officer.

The coordinator never invents a reason: every reason traces back to a node
decision that is logged in ``state["decisions"]``.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from .state import AgriPulseState

log = logging.getLogger("agridoc.agents.coordinator")


def _tool(state: AgriPulseState) -> Dict[str, str | List[str]]:
    """Produce the final plan from the accumulated state."""
    uncertain = state.get("uncertain", False)
    call_expert = state.get("call_expert", False)
    weather_risk = state.get("weather_risk", "unknown")
    sell_rec = state.get("sell_recommendation", "unknown")
    confidence = state.get("confidence", 0.0)

    # 1. Safety first: escalate when the model is unsure or the disease is severe.
    if call_expert or uncertain:
        return {
            "plan": "call_expert",
            "reasons": [
                "Confidence is low or the disease is severe — an agriculture officer should verify.",
            ],
        }

    # 2. Treatment timing vs weather.
    if weather_risk == "high":
        return {
            "plan": "wait",
            "reasons": [
                "Heavy rain is expected — spraying now wastes fungicide and may cause run-off. Wait for dry leaves.",
            ],
        }
    if weather_risk == "medium":
        return {
            "plan": "wait_48h",
            "reasons": [
                "Rain is likely within 48h — treat after the soil dries and leaves are dry.",
            ],
        }

    # 3. Sell signal.
    if sell_rec == "sell_now":
        return {
            "plan": "sell_now",
            "reasons": [
                "Market prices are falling or stable — sell harvestable produce now to avoid spoilage, then treat the rest.",
            ],
        }
    if sell_rec == "hold":
        return {
            "plan": "hold",
            "reasons": [
                "Market prices are rising — treat now and hold for a better price.",
            ],
        }

    return {
        "plan": "treat_now",
        "reasons": [
            "Dry weather and no urgent price pressure — treat now to stop the disease spreading.",
        ],
    }


def node(state: AgriPulseState) -> AgriPulseState:
    """LangGraph node: emit the final plan."""
    result = _tool(state)
    state["plan"] = result["plan"]
    state["reasons"] = result["reasons"]
    state["decisions"].append(f"coordinator: plan={state['plan']}")
    return state